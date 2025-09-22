import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

User = get_user_model()

class IntentPurpose(models.TextChoices):
    WALLET_TOPUP = 'wallet_topup', 'Wallet Top-up'
    ORDER_PAYMENT = 'order_payment', 'Order Payment'


class PaymentStatus(models.TextChoices):
    REQUIRES_PAYMENT_METHOD = 'requires_payment_method', 'Requires Payment Method'
    PROCESSING = 'processing', 'Processing'
    SUCCEEDED = 'succeeded', 'Succeeded'
    FAILED = 'failed', 'Failed'
    EXPIRED = 'expired', 'Expired'


class PayOrder(models.Model):
    """
    Đơn hàng có thể được thanh toán qua payment intents.
    """
    order_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_comment="Người tạo đơn hàng"
    )
    total_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        db_comment="Tổng giá trị đơn hàng"
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('paid', 'Paid'),
            ('cancelled', 'Cancelled'),
            ('expired', 'Expired'),
        ],
        default='pending',
        db_comment="Trạng thái đơn hàng"
    )
    description = models.TextField(
        blank=True,
        db_comment="Mô tả đơn hàng"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        db_comment="Dữ liệu bổ sung của đơn hàng"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pay_orders"
        db_table_comment = "Đơn hàng có thể được thanh toán qua payment intents."
        indexes = [
            models.Index(fields=['user'], name='idx_pay_orders_user'),
            models.Index(fields=['status'], name='idx_pay_orders_status'),
            models.Index(fields=['created_at'], name='idx_pay_orders_created'),
        ]

    def __str__(self):
        return f"Order {self.order_id} - {self.status} - {self.total_amount}"


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


class PayWalletLedger(models.Model):
    """
    Nguồn sự thật cho tất cả giao dịch ví. Mọi thay đổi số dư phải đi qua ledger này.
    """
    TX_TYPE_CHOICES = [
        ('deposit', 'Deposit'),
        ('withdraw', 'Withdraw'),
        ('payment', 'Payment'),
        ('refund', 'Refund'),
        ('adjustment', 'Adjustment'),
    ]

    ledger_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(
        PayWallet,
        on_delete=models.CASCADE,
        related_name='ledger_entries',
        db_comment="Ví bị ảnh hưởng"
    )
    tx_type = models.CharField(
        max_length=20,
        choices=TX_TYPE_CHOICES,
        db_comment="Loại giao dịch: deposit | withdraw | payment | refund | adjustment"
    )
    amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        db_comment="Số tiền giao dịch (luôn là số dương)"
    )
    is_credit = models.BooleanField(
        db_comment="true = cộng tiền, false = trừ tiền"
    )
    balance_before = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        db_comment="Số dư trước giao dịch"
    )
    balance_after = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        db_comment="Số dư sau giao dịch"
    )
    payment = models.ForeignKey(
        'PayPayment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ledger_entries',
        db_comment="Payment liên quan (nếu có)"
    )
    description = models.TextField(
        blank=True,
        db_comment="Mô tả giao dịch"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        db_comment="Dữ liệu bổ sung"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "pay_wallet_ledger"
        db_table_comment = "Nguồn sự thật cho tất cả giao dịch ví. Mọi thay đổi số dư phải đi qua ledger này."
        indexes = [
            models.Index(fields=['wallet', 'created_at'], name='idx_wallet_ledger_wallet'),
            models.Index(fields=['payment'], name='idx_wallet_ledger_payment'),
            models.Index(fields=['tx_type'], name='idx_wallet_ledger_tx_type'),
        ]
        ordering = ['-created_at']

    def __str__(self):
        sign = '+' if self.is_credit else '-'
        return f"Ledger {self.wallet.user.username} {sign}{self.amount} -> {self.balance_after}"

    def save(self, *args, **kwargs):
        """Validate balance calculation"""
        if self.is_credit:
            expected_balance = self.balance_before + self.amount
        else:
            expected_balance = self.balance_before - self.amount
        
        if self.balance_after != expected_balance:
            raise ValueError(f"Balance calculation error: expected {expected_balance}, got {self.balance_after}")
        
        super().save(*args, **kwargs)


class PayPaymentIntent(models.Model):
    """
    Một yêu cầu thu tiền. Provider cố định là SePay (chính sách hệ thống).
    """
    intent_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_comment="Ai đang thanh toán"
    )
    order = models.ForeignKey(
        PayOrder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_comment="Liên kết nếu là thanh toán đơn"
    )
    purpose = models.CharField(
        max_length=20,
        choices=IntentPurpose.choices,
        db_comment="wallet_topup (nạp ví) | order_payment (mua trực tiếp)"
    )
    amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        db_comment="Số tiền phải trả"
    )
    status = models.CharField(
        max_length=30,
        choices=PaymentStatus.choices,
        default=PaymentStatus.REQUIRES_PAYMENT_METHOD,
        db_comment="Trạng thái luồng thanh toán"
    )
    order_code = models.CharField(
        max_length=255,
        unique=True,
        db_comment="Chuỗi đối soát CK (nội dung chuyển khoản). Cần duy nhất để match."
    )
    return_url = models.TextField(
        null=True,
        blank=True,
        db_comment="URL trở về khi thanh toán xong (nếu dùng webflow)"
    )
    cancel_url = models.TextField(
        null=True,
        blank=True,
        db_comment="URL trở về khi hủy"
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        db_comment="Hạn sử dụng intent/QR"
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
        db_table_comment = "Một yêu cầu thu tiền. Provider cố định là SePay (chính sách hệ thống)."
        indexes = [
            models.Index(fields=['user', 'status'], name='idx_pay_intents_user_status'),
            models.Index(fields=['order'], name='idx_pay_intents_order'),
        ]

    def __str__(self):
        return f"Intent {self.intent_id} - {self.status} - {self.amount}"

    @property
    def is_expired(self):
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at

    @property
    def is_pending(self):
        return self.status in [PaymentStatus.REQUIRES_PAYMENT_METHOD, PaymentStatus.PROCESSING]

    @property
    def is_completed(self):
        return self.status in [PaymentStatus.SUCCEEDED, PaymentStatus.FAILED, PaymentStatus.EXPIRED]

    def expire(self):
        """Mark intent as expired"""
        if self.is_pending:
            self.status = PaymentStatus.EXPIRED
            self.save(update_fields=['status', 'updated_at'])

    def succeed(self):
        """Mark intent as succeeded"""
        self.status = PaymentStatus.SUCCEEDED
        self.save(update_fields=['status', 'updated_at'])

    def fail(self):
        """Mark intent as failed"""
        self.status = PaymentStatus.FAILED
        self.save(update_fields=['status', 'updated_at'])


class PayPaymentAttempt(models.Model):
    """
    Một intent có thể có nhiều attempt (tạo lại QR, đổi số tiền...). Provider cố định: SePay.
    """
    attempt_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    intent = models.ForeignKey(
        PayPaymentIntent,
        on_delete=models.CASCADE,
        db_comment="Thuộc intent nào"
    )
    status = models.CharField(
        max_length=30,
        choices=PaymentStatus.choices,
        default=PaymentStatus.REQUIRES_PAYMENT_METHOD,
        db_comment="Tiến trình attempt"
    )
    bank_code = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        db_comment="VCB/MB/BIDV... (SePay)"
    )
    account_number = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        db_comment="STK nhận hoặc VA theo đơn"
    )
    account_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_comment="Tên tài khoản nhận"
    )
    transfer_content = models.TextField(
        null=True,
        blank=True,
        db_comment="Nội dung CK chính xác để auto-match"
    )
    transfer_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
        db_comment="Số tiền hiển thị trên QR (có thể khóa cứng)"
    )
    qr_image_url = models.TextField(
        null=True,
        blank=True,
        db_comment="Link ảnh QR động VietQR (SePay)"
    )
    qr_svg = models.TextField(
        null=True,
        blank=True,
        db_comment="Dữ liệu SVG QR nếu render trực tiếp"
    )
    provider_session_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_comment="Mã phiên/khoá phía SePay nếu có"
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        db_comment="Hết hạn phiên attempt/QR"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        db_comment="Payload bổ sung"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "pay_payment_attempts"
        db_table_comment = "Một intent có thể có nhiều attempt (tạo lại QR, đổi số tiền...). Provider cố định: SePay."
        indexes = [
            models.Index(fields=['intent'], name='idx_pay_attempts_intent'),
        ]

    def __str__(self):
        return f"Attempt {self.attempt_id} - Intent {self.intent.intent_id} - {self.status}"


class PayPayment(models.Model):
    """
    Bút toán thanh toán ở cấp "gateway". Khi succeeded: nếu là nạp ví → ghi credit ledger; 
    nếu là order → chuyển order sang paid, cấp license.
    """
    payment_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_comment="Người thực hiện thanh toán"
    )
    order = models.ForeignKey(
        PayOrder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_comment="Đơn hàng liên quan (nếu có)"
    )
    intent = models.ForeignKey(
        PayPaymentIntent,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_comment="Intent dẫn đến payment này"
    )
    amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        db_comment="Số tiền thanh toán"
    )
    status = models.CharField(
        max_length=30,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PROCESSING,
        db_comment="Trạng thái chốt sau khi đối soát"
    )
    provider_payment_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_comment="ID giao dịch SePay (sepay_tx_id) để tra soát"
    )
    message = models.TextField(
        null=True,
        blank=True,
        db_comment="Ghi chú trạng thái (VD: Lý do failed)"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        db_comment="Payload bổ sung (bản đồ đối soát, sai số...)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pay_payments"
        db_table_comment = "Bút toán thanh toán ở cấp gateway. Khi succeeded: nếu là nạp ví → ghi credit ledger; nếu là order → chuyển order sang paid, cấp license."
        indexes = [
            models.Index(fields=['user', 'created_at'], name='idx_pay_payments_user_created'),
            models.Index(fields=['intent'], name='idx_pay_payments_intent'),
            models.Index(fields=['order'], name='idx_pay_payments_order'),
        ]

    def __str__(self):
        return f"Payment {self.payment_id} - {self.status} - {self.amount}"


class PaySepayWebhookEvent(models.Model):
    """
    Inbox webhook của SePay. Ta luôn lưu thô trước, sau đó mới parse và xử lý để đảm bảo an toàn.
    """
    webhook_event_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sepay_tx_id = models.BigIntegerField(
        unique=True,
        db_comment="ID duy nhất từ SePay để idempotent (tránh xử lý trùng)"
    )
    received_at = models.DateTimeField(auto_now_add=True)
    payload = models.JSONField(
        db_comment="Lưu nguyên phần thân webhook để debug/đối soát"
    )
    processed = models.BooleanField(
        default=False,
        db_comment="Đã xử lý phát sinh payment/ledger chưa"
    )
    process_error = models.TextField(
        null=True,
        blank=True,
        db_comment="Thông tin lỗi nếu xử lý thất bại"
    )

    class Meta:
        db_table = "pay_sepay_webhook_events"
        db_table_comment = "Inbox webhook của SePay. Ta luôn lưu thô trước, sau đó mới parse và xử lý để đảm bảo an toàn."
        indexes = [
            models.Index(fields=['sepay_tx_id'], name='idx_sepay_webhooks_tx_id'),
            models.Index(fields=['processed'], name='idx_sepay_webhooks_processed'),
            models.Index(fields=['received_at'], name='idx_sepay_webhooks_received'),
        ]

    def __str__(self):
        return f"Webhook {self.webhook_event_id} - TX {self.sepay_tx_id} - Processed: {self.processed}"


class PayBankTransaction(models.Model):
    """
    Bảng đối soát chủ động từ API SePay: id, số tiền, nội dung, tham chiếu…
    """
    sepay_tx_id = models.BigIntegerField(
        primary_key=True,
        db_comment="Khớp với provider_payment_id khi đã xử lý"
    )
    transaction_date = models.DateTimeField(
        db_comment="Thời gian giao dịch ngân hàng"
    )
    account_number = models.CharField(
        max_length=50,
        db_comment="STK nhận tiền"
    )
    amount_in = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal('0.00'),
        db_comment="Tiền vào (nạp ví/ thanh toán)"
    )
    amount_out = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal('0.00'),
        db_comment="Tiền ra (ít dùng)"
    )
    content = models.TextField(
        null=True,
        blank=True,
        db_comment="Nội dung CK (chứa order_code để auto-match)"
    )
    reference_number = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_comment="Mã tham chiếu của ngân hàng"
    )
    bank_code = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        db_comment="VCB/MB/BIDV..."
    )
    intent = models.ForeignKey(
        PayPaymentIntent,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_comment="Khớp được intent nào"
    )
    attempt = models.ForeignKey(
        PayPaymentAttempt,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_comment="Khớp được attempt nào"
    )
    payment = models.ForeignKey(
        PayPayment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_comment="Payment được tạo/chốt từ giao dịch này"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "pay_bank_transactions"
        db_table_comment = "Bảng đối soát chủ động từ API SePay: id, số tiền, nội dung, tham chiếu…"
        indexes = [
            models.Index(fields=['intent'], name='idx_bank_tx_intent'),
            models.Index(fields=['reference_number'], name='idx_bank_tx_reference'),
            models.Index(fields=['account_number'], name='idx_bank_tx_account'),
        ]

    def __str__(self):
        return f"Bank TX {self.sepay_tx_id} - {self.amount_in} - {self.account_number}"


class SeapayOrder(models.Model):
    """Legacy model - use PayPaymentIntent instead"""
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("failed", "Failed"),
    ]

    def __str__(self):
        return f"Order {self.id} - {self.status}"
