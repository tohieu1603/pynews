import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

User = get_user_model()


class PayWallet(models.Model):
    """
    Ví điện tử của user. Mỗi user có 1 ví / 1 loại tiền.
    Tất cả thay đổi số dư đi qua pay_wallet_ledger.
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('suspended', 'Suspended'),
    ]
    
    CURRENCY_CHOICES = [
        ('VND', 'Vietnamese Dong'),
        ('USD', 'US Dollar'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        unique=True,
        db_comment="Chủ ví"
    )
    balance = models.DecimalField(
        max_digits=18, 
        decimal_places=2, 
        default=Decimal('0.00'),
        db_comment="Số dư hiện tại, chỉ cập nhật qua ledger"
    )
    currency = models.CharField(
        max_length=10, 
        choices=CURRENCY_CHOICES,
        default='VND',
        db_comment="Loại tiền (VNĐ, USD...)"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        db_comment="active | suspended (khóa tạm thời)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pay_wallets"
        db_table_comment = "Mỗi user có 1 ví / 1 loại tiền. Tất cả thay đổi số dư đi qua pay_wallet_ledger."
        indexes = [
            models.Index(fields=['user'], name='idx_pay_wallets_user'),
        ]
        constraints = [
            models.UniqueConstraint(fields=['user'], name='unique_user_wallet')
        ]

    def __str__(self):
        return f"Wallet {self.user.username} - {self.balance} {self.currency}"

    @property
    def is_active(self):
        return self.status == 'active'


class PayPaymentIntent(models.Model):
    """
    Intent thanh toán. order_code ~ content, reference_code ~ callback id từ SePay.
    """
    PURPOSE_CHOICES = [
        ('wallet_topup', 'Wallet Top-up'),
        ('order_payment', 'Order Payment'),
        ('withdraw', 'Withdraw'),
    ]
    
    STATUS_CHOICES = [
        ('requires_payment_method', 'Requires Payment Method'),
        ('processing', 'Processing'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('expired', 'Expired'),
    ]
    
    PROVIDER_CHOICES = [
        ('sepay', 'SePay'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_comment="Ai thực hiện thanh toán"
    )
    wallet = models.ForeignKey(
        PayWallet,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_comment="Ví bị ảnh hưởng (nếu là nạp tiền/rút tiền)"
    )
    
    provider = models.CharField(
        max_length=20,
        choices=PROVIDER_CHOICES,
        default='sepay',
        db_comment="Nhà cung cấp thanh toán (hiện tại chỉ SePay)"
    )
    purpose = models.CharField(
        max_length=20,
        choices=PURPOSE_CHOICES,
        db_comment="wallet_topup | order_payment | withdraw"
    )
    amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        db_comment="Số tiền cần thanh toán"
    )
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='requires_payment_method',
        db_comment="requires_payment_method | processing | succeeded | failed | expired"
    )
    order_code = models.CharField(
        max_length=100,
        unique=True,
        db_comment="Chuỗi đối soát CK (nội dung chuyển khoản). Match với content từ SePay."
    )
    reference_code = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        db_comment="Mã tham chiếu từ SePay (referenceCode) để tránh trùng lặp giao dịch"
    )
    return_url = models.TextField(
        null=True,
        blank=True,
        db_comment="URL trở về khi thanh toán xong (webflow)"
    )
    cancel_url = models.TextField(
        null=True,
        blank=True,
        db_comment="URL trở về khi hủy"
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        db_comment="Hạn dùng intent/QR"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        db_comment="Payload bổ sung (IP, UA, campaign...)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pay_payment_intents"
        db_table_comment = "Intent thanh toán. order_code ~ content, reference_code ~ callback id từ SePay."
        indexes = [
            models.Index(fields=['user', 'status'], name='idx_pay_intents_user_status'),
            models.Index(fields=['reference_code'], name='idx_pay_intents_reference'),
            models.Index(fields=['order_code'], name='idx_pay_intents_order_code'),
            models.Index(fields=['created_at'], name='idx_pay_intents_created'),
        ]

    def __str__(self):
        return f"Intent {self.order_code} - {self.status} - {self.amount}"

    @property
    def is_expired(self):
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at

    @property
    def is_pending(self):
        return self.status in ['requires_payment_method', 'processing']

    @property
    def is_completed(self):
        return self.status in ['succeeded', 'failed', 'expired']

    def expire(self):
        """Mark intent as expired"""
        if self.is_pending:
            self.status = 'expired'
            self.save(update_fields=['status', 'updated_at'])

    def succeed(self, reference_code=None):
        """Mark intent as succeeded"""
        self.status = 'succeeded'
        if reference_code:
            self.reference_code = reference_code
        self.save(update_fields=['status', 'reference_code', 'updated_at'])

    def fail(self):
        """Mark intent as failed"""
        self.status = 'failed'
        self.save(update_fields=['status', 'updated_at'])


class SeapayOrder(models.Model):
    """Legacy model - use PayPaymentIntent instead"""
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("failed", "Failed"),
    ]

    def __str__(self):
        return f"Order {self.id} - {self.status}"
