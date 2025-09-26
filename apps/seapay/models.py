import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

User = get_user_model()

class IntentPurpose(models.TextChoices):
    WALLET_TOPUP = 'wallet_topup', 'Wallet Top-up'
    ORDER_PAYMENT = 'order_payment', 'Order Payment'
    SYMBOL_PURCHASE = 'symbol_purchase', 'Symbol Purchase'
    WITHDRAW = 'withdraw', 'Withdraw'


class PaymentStatus(models.TextChoices):
    REQUIRES_PAYMENT_METHOD = 'requires_payment_method', 'Requires Payment Method'
    PROCESSING = 'processing', 'Processing'
    SUCCEEDED = 'succeeded', 'Succeeded'
    FAILED = 'failed', 'Failed'
    EXPIRED = 'expired', 'Expired'


class OrderStatus(models.TextChoices):
    PENDING_PAYMENT = 'pending_payment', 'Pending Payment'
    PAID = 'paid', 'Paid'
    FAILED = 'failed', 'Failed'
    CANCELLED = 'cancelled', 'Cancelled'
    REFUNDED = 'refunded', 'Refunded'


class PaymentMethod(models.TextChoices):
    WALLET = 'wallet', 'Wallet Balance'
    SEPAY_TRANSFER = 'sepay_transfer', 'SePay Transfer (QR/Bank)'


class LicenseStatus(models.TextChoices):
    ACTIVE = 'active', 'Active'
    EXPIRED = 'expired', 'Expired'
    SUSPENDED = 'suspended', 'Suspended'
    REVOKED = 'revoked', 'Revoked'


class WalletTxType(models.TextChoices):
    DEPOSIT = 'deposit', 'NÃ¡ÂºÂ¡p tiÃ¡Â»Ân (tÃ¡Â»Â« SePay)'
    PURCHASE = 'purchase', 'Mua bot'
    REFUND = 'refund', 'HoÃƒÂ n tiÃ¡Â»Ân'
    WITHDRAWAL = 'withdrawal', 'RÃƒÂºt tiÃ¡Â»Ân'
    TRANSFER_IN = 'transfer_in', 'ChuyÃ¡Â»Æ’n Ã„â€˜Ã¡ÂºÂ¿n'
    TRANSFER_OUT = 'transfer_out', 'ChuyÃ¡Â»Æ’n Ã„â€˜i'


class PayOrder(models.Model):
    """
    Ã„ÂÃ†Â¡n hÃƒÂ ng cÃƒÂ³ thÃ¡Â»Æ’ Ã„â€˜Ã†Â°Ã¡Â»Â£c thanh toÃƒÂ¡n qua payment intents.
    """
    order_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_comment="NgÃ†Â°Ã¡Â»Âi tÃ¡ÂºÂ¡o Ã„â€˜Ã†Â¡n hÃƒÂ ng"
    )
    total_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        db_comment="TÃ¡Â»â€¢ng giÃƒÂ¡ trÃ¡Â»â€¹ Ã„â€˜Ã†Â¡n hÃƒÂ ng"
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
        db_comment="TrÃ¡ÂºÂ¡ng thÃƒÂ¡i Ã„â€˜Ã†Â¡n hÃƒÂ ng"
    )
    description = models.TextField(
        blank=True,
        db_comment="MÃƒÂ´ tÃ¡ÂºÂ£ Ã„â€˜Ã†Â¡n hÃƒÂ ng"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        db_comment="DÃ¡Â»Â¯ liÃ¡Â»â€¡u bÃ¡Â»â€¢ sung cÃ¡Â»Â§a Ã„â€˜Ã†Â¡n hÃƒÂ ng"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pay_orders"
        db_table_comment = "Ã„ÂÃ†Â¡n hÃƒÂ ng cÃƒÂ³ thÃ¡Â»Æ’ Ã„â€˜Ã†Â°Ã¡Â»Â£c thanh toÃƒÂ¡n qua payment intents."
        indexes = [
            models.Index(fields=['user'], name='idx_pay_orders_user'),
            models.Index(fields=['status'], name='idx_pay_orders_status'),
            models.Index(fields=['created_at'], name='idx_pay_orders_created'),
        ]

    def __str__(self):
        return f"Order {self.order_id} - {self.status} - {self.total_amount}"


class PayWallet(models.Model):
    """
    VÃƒÂ­ Ã„â€˜iÃ¡Â»â€¡n tÃ¡Â»Â­ cÃ¡Â»Â§a user. MÃ¡Â»â€”i user cÃƒÂ³ 1 vÃƒÂ­ / 1 loÃ¡ÂºÂ¡i tiÃ¡Â»Ân.
    TÃ¡ÂºÂ¥t cÃ¡ÂºÂ£ thay Ã„â€˜Ã¡Â»â€¢i sÃ¡Â»â€˜ dÃ†Â° Ã„â€˜i qua pay_wallet_ledger.
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
        db_comment="ChÃ¡Â»Â§ vÃƒÂ­"
    )
    balance = models.DecimalField(
        max_digits=18, 
        decimal_places=2, 
        default=Decimal('0.00'),
        db_comment="SÃ¡Â»â€˜ dÃ†Â° hiÃ¡Â»â€¡n tÃ¡ÂºÂ¡i, chÃ¡Â»â€° cÃ¡ÂºÂ­p nhÃ¡ÂºÂ­t qua ledger"
    )
    currency = models.CharField(
        max_length=10, 
        choices=CURRENCY_CHOICES,
        default='VND',
        db_comment="LoÃ¡ÂºÂ¡i tiÃ¡Â»Ân (VNÃ„Â, USD...)"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        db_comment="active | suspended (khÃƒÂ³a tÃ¡ÂºÂ¡m thÃ¡Â»Âi)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pay_wallets"
        db_table_comment = "MÃ¡Â»â€”i user cÃƒÂ³ 1 vÃƒÂ­ / 1 loÃ¡ÂºÂ¡i tiÃ¡Â»Ân. TÃ¡ÂºÂ¥t cÃ¡ÂºÂ£ thay Ã„â€˜Ã¡Â»â€¢i sÃ¡Â»â€˜ dÃ†Â° Ã„â€˜i qua pay_wallet_ledger."
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
    NguÃ¡Â»â€œn sÃ¡Â»Â± thÃ¡ÂºÂ­t cho tÃ¡ÂºÂ¥t cÃ¡ÂºÂ£ giao dÃ¡Â»â€¹ch vÃƒÂ­. MÃ¡Â»Âi thay Ã„â€˜Ã¡Â»â€¢i sÃ¡Â»â€˜ dÃƒÂ¹ phÃ¡ÂºÂ£i Ã„â€˜i qua ledger nÃƒÂ y.
    """
    ledger_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(
        PayWallet,
        on_delete=models.CASCADE,
        related_name='ledger_entries',
        db_comment="VÃƒÂ­ bÃ¡Â»â€¹ Ã¡ÂºÂ£nh hÃ†Â°Ã¡Â»Å¸ng"
    )
    tx_type = models.CharField(
        max_length=20,
        choices=WalletTxType.choices,
        db_comment="LoÃ¡ÂºÂ¡i biÃ¡ÂºÂ¿n Ã„â€˜Ã¡Â»â„¢ng: nÃ¡ÂºÂ¡p/purchase/hoÃƒÂ n tiÃ¡Â»Ân/..."
    )
    amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        db_comment="LuÃƒÂ´n > 0; chiÃ¡Â»Âu thÃ¡Â»Æ’ hiÃ¡Â»â€¡n bÃ¡ÂºÂ±ng is_credit"
    )
    is_credit = models.BooleanField(
        db_comment="true: cÃ¡Â»â„¢ng vÃƒÂ­; false: trÃ¡Â»Â« vÃƒÂ­"
    )
    balance_before = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        db_comment="SÃ¡Â»â€˜ dÃ†Â° trÃ†Â°Ã¡Â»â€ºc giao dÃ¡Â»â€¹ch"
    )
    balance_after = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        db_comment="SÃ¡Â»â€˜ dÃ†Â° ngay sau giao dÃ¡Â»â€¹ch nÃƒÂ y"
    )
    order = models.ForeignKey(
        'PaySymbolOrder',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_comment="LiÃƒÂªn kÃ¡ÂºÂ¿t Ã„â€˜Ã†Â¡n hÃƒÂ ng khi lÃƒÂ  purchase/refund"
    )
    payment = models.ForeignKey(
        'PayPayment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ledger_entries',
        db_comment="BÃ¡ÂºÂ¯t buÃ¡Â»â„¢c vÃ¡Â»â€ºi deposit (nÃ¡ÂºÂ¡p qua SePay)"
    )
    note = models.TextField(
        blank=True,
        db_comment="DiÃ¡Â»â€¦n giÃ¡ÂºÂ£i ngÃ¡ÂºÂ¯n gÃ¡Â»Ân cho bÃ¡ÂºÂ£n ghi sÃ¡Â»â€¢ cÃƒÂ¡i"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        db_comment="Payload bÃ¡Â»â€¢ sung: ip, device, source, ..."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "pay_wallet_ledger"
        db_table_comment = "Quy tÃ¡ÂºÂ¯c: deposit phÃ¡ÂºÂ£i cÃƒÂ³ payment_id (SePay); purchase phÃ¡ÂºÂ£i cÃƒÂ³ order_id. SÃ¡Â»â€¢ cÃƒÂ¡i lÃƒÂ  nguÃ¡Â»â€œn sÃ¡Â»Â± thÃ¡ÂºÂ­t Ã„â€˜Ã¡Â»Æ’ tÃƒÂ­nh balance."
        indexes = [
            models.Index(fields=['wallet', 'created_at'], name='idx_ledger_wallet_created'),
            models.Index(fields=['payment'], name='idx_ledger_payment'),
            models.Index(fields=['tx_type'], name='idx_ledger_tx_type'),
            models.Index(fields=['order'], name='idx_ledger_order'),
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
    MÃ¡Â»â„¢t yÃƒÂªu cÃ¡ÂºÂ§u thu tiÃ¡Â»Ân. Provider cÃ¡Â»â€˜ Ã„â€˜Ã¡Â»â€¹nh lÃƒÂ  SePay (chÃƒÂ­nh sÃƒÂ¡ch hÃ¡Â»â€¡ thÃ¡Â»â€˜ng).
    """
    intent_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_comment="Ai Ã„â€˜ang thanh toÃƒÂ¡n"
    )
    order = models.ForeignKey(
        'PaySymbolOrder',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_comment="LiÃƒÂªn kÃ¡ÂºÂ¿t nÃ¡ÂºÂ¿u lÃƒÂ  thanh toÃƒÂ¡n Ã„â€˜Ã†Â¡n"
    )
    purpose = models.CharField(
        max_length=20,
        choices=IntentPurpose.choices,
        db_comment="wallet_topup (nÃ¡ÂºÂ¡p vÃƒÂ­) | order_payment (mua trÃ¡Â»Â±c tiÃ¡ÂºÂ¿p)"
    )
    amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        db_comment="SÃ¡Â»â€˜ tiÃ¡Â»Ân phÃ¡ÂºÂ£i trÃ¡ÂºÂ£"
    )
    status = models.CharField(
        max_length=30,
        choices=PaymentStatus.choices,
        default=PaymentStatus.REQUIRES_PAYMENT_METHOD,
        db_comment="TrÃ¡ÂºÂ¡ng thÃƒÂ¡i luÃ¡Â»â€œng thanh toÃƒÂ¡n"
    )
    order_code = models.CharField(
        max_length=255,
        unique=True,
        db_comment="ChuÃ¡Â»â€”i Ã„â€˜Ã¡Â»â€˜i soÃƒÂ¡t CK (nÃ¡Â»â„¢i dung chuyÃ¡Â»Æ’n khoÃ¡ÂºÂ£n). CÃ¡ÂºÂ§n duy nhÃ¡ÂºÂ¥t Ã„â€˜Ã¡Â»Æ’ match."
    )
    reference_code = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_comment='Reference code returned by provider for reconciliation'
    )
    return_url = models.TextField(
        null=True,
        blank=True,
        db_comment="URL trÃ¡Â»Å¸ vÃ¡Â»Â khi thanh toÃƒÂ¡n xong (nÃ¡ÂºÂ¿u dÃƒÂ¹ng webflow)"
    )
    cancel_url = models.TextField(
        null=True,
        blank=True,
        db_comment="URL trÃ¡Â»Å¸ vÃ¡Â»Â khi hÃ¡Â»Â§y"
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        db_comment="HÃ¡ÂºÂ¡n sÃ¡Â»Â­ dÃ¡Â»Â¥ng intent/QR"
    )
    qr_code_url = models.TextField(
        null=True,
        blank=True,
        db_comment="QR code URL for payment"
    )
    deep_link = models.TextField(
        null=True,
        blank=True,
        db_comment="Deep link for mobile payment"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        db_comment="Payload bÃ¡Â»â€¢ sung (IP, UA, campaign...)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pay_payment_intents"
        db_table_comment = "MÃ¡Â»â„¢t yÃƒÂªu cÃ¡ÂºÂ§u thu tiÃ¡Â»Ân. Provider cÃ¡Â»â€˜ Ã„â€˜Ã¡Â»â€¹nh lÃƒÂ  SePay (chÃƒÂ­nh sÃƒÂ¡ch hÃ¡Â»â€¡ thÃ¡Â»â€˜ng)."
        indexes = [
            models.Index(fields=['user', 'status'], name='idx_pay_intents_user_status'),
            models.Index(fields=['order'], name='idx_pay_intents_order'),
        ]

    def __str__(self):
        return f"Intent {self.intent_id} - {self.status} - {self.amount}"

    def is_expired(self):
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at

    def is_pending(self):
        return self.status in [PaymentStatus.REQUIRES_PAYMENT_METHOD, PaymentStatus.PROCESSING]

    @property
    def is_completed(self):
        return self.status in [PaymentStatus.SUCCEEDED, PaymentStatus.FAILED, PaymentStatus.EXPIRED]

    def expire(self):
        """Mark intent as expired"""
        if self.is_pending():
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
    MÃ¡Â»â„¢t intent cÃƒÂ³ thÃ¡Â»Æ’ cÃƒÂ³ nhiÃ¡Â»Âu attempt (tÃ¡ÂºÂ¡o lÃ¡ÂºÂ¡i QR, Ã„â€˜Ã¡Â»â€¢i sÃ¡Â»â€˜ tiÃ¡Â»Ân...). Provider cÃ¡Â»â€˜ Ã„â€˜Ã¡Â»â€¹nh: SePay.
    """
    attempt_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    intent = models.ForeignKey(
        PayPaymentIntent,
        on_delete=models.CASCADE,
        db_comment="ThuÃ¡Â»â„¢c intent nÃƒÂ o"
    )
    status = models.CharField(
        max_length=30,
        choices=PaymentStatus.choices,
        default=PaymentStatus.REQUIRES_PAYMENT_METHOD,
        db_comment="TiÃ¡ÂºÂ¿n trÃƒÂ¬nh attempt"
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
        db_comment="STK nhÃ¡ÂºÂ­n hoÃ¡ÂºÂ·c VA theo Ã„â€˜Ã†Â¡n"
    )
    account_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_comment="TÃƒÂªn tÃƒÂ i khoÃ¡ÂºÂ£n nhÃ¡ÂºÂ­n"
    )
    transfer_content = models.TextField(
        null=True,
        blank=True,
        db_comment="NÃ¡Â»â„¢i dung CK chÃƒÂ­nh xÃƒÂ¡c Ã„â€˜Ã¡Â»Æ’ auto-match"
    )
    transfer_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
        db_comment="SÃ¡Â»â€˜ tiÃ¡Â»Ân hiÃ¡Â»Æ’n thÃ¡Â»â€¹ trÃƒÂªn QR (cÃƒÂ³ thÃ¡Â»Æ’ khÃƒÂ³a cÃ¡Â»Â©ng)"
    )
    qr_image_url = models.TextField(
        null=True,
        blank=True,
        db_comment="Link Ã¡ÂºÂ£nh QR Ã„â€˜Ã¡Â»â„¢ng VietQR (SePay)"
    )
    qr_svg = models.TextField(
        null=True,
        blank=True,
        db_comment="DÃ¡Â»Â¯ liÃ¡Â»â€¡u SVG QR nÃ¡ÂºÂ¿u render trÃ¡Â»Â±c tiÃ¡ÂºÂ¿p"
    )
    provider_session_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_comment="MÃƒÂ£ phiÃƒÂªn/khoÃƒÂ¡ phÃƒÂ­a SePay nÃ¡ÂºÂ¿u cÃƒÂ³"
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        db_comment="HÃ¡ÂºÂ¿t hÃ¡ÂºÂ¡n phiÃƒÂªn attempt/QR"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        db_comment="Payload bÃ¡Â»â€¢ sung"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "pay_payment_attempts"
        db_table_comment = "MÃ¡Â»â„¢t intent cÃƒÂ³ thÃ¡Â»Æ’ cÃƒÂ³ nhiÃ¡Â»Âu attempt (tÃ¡ÂºÂ¡o lÃ¡ÂºÂ¡i QR, Ã„â€˜Ã¡Â»â€¢i sÃ¡Â»â€˜ tiÃ¡Â»Ân...). Provider cÃ¡Â»â€˜ Ã„â€˜Ã¡Â»â€¹nh: SePay."
        indexes = [
            models.Index(fields=['intent'], name='idx_pay_attempts_intent'),
        ]

    def __str__(self):
        return f"Attempt {self.attempt_id} - Intent {self.intent.intent_id} - {self.status}"


class PayPayment(models.Model):
    """
    BÃƒÂºt toÃƒÂ¡n thanh toÃƒÂ¡n Ã¡Â»Å¸ cÃ¡ÂºÂ¥p "gateway". Khi succeeded: nÃ¡ÂºÂ¿u lÃƒÂ  nÃ¡ÂºÂ¡p vÃƒÂ­ Ã¢â€ â€™ ghi credit ledger; 
    nÃ¡ÂºÂ¿u lÃƒÂ  order Ã¢â€ â€™ chuyÃ¡Â»Æ’n order sang paid, cÃ¡ÂºÂ¥p license.
    """
    payment_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_comment="NgÃ†Â°Ã¡Â»Âi thÃ¡Â»Â±c hiÃ¡Â»â€¡n thanh toÃƒÂ¡n"
    )
    order = models.ForeignKey(
        'PaySymbolOrder',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_comment="Ã„ÂÃ†Â¡n hÃƒÂ ng liÃƒÂªn quan (nÃ¡ÂºÂ¿u cÃƒÂ³)"
    )
    intent = models.ForeignKey(
        PayPaymentIntent,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_comment="Intent dÃ¡ÂºÂ«n Ã„â€˜Ã¡ÂºÂ¿n payment nÃƒÂ y"
    )
    amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        db_comment="SÃ¡Â»â€˜ tiÃ¡Â»Ân thanh toÃƒÂ¡n"
    )
    status = models.CharField(
        max_length=30,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PROCESSING,
        db_comment="TrÃ¡ÂºÂ¡ng thÃƒÂ¡i chÃ¡Â»â€˜t sau khi Ã„â€˜Ã¡Â»â€˜i soÃƒÂ¡t"
    )
    provider_payment_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_comment="ID giao dÃ¡Â»â€¹ch SePay (sepay_tx_id) Ã„â€˜Ã¡Â»Æ’ tra soÃƒÂ¡t"
    )
    message = models.TextField(
        null=True,
        blank=True,
        db_comment="Ghi chÃƒÂº trÃ¡ÂºÂ¡ng thÃƒÂ¡i (VD: LÃƒÂ½ do failed)"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        db_comment="Payload bÃ¡Â»â€¢ sung (bÃ¡ÂºÂ£n Ã„â€˜Ã¡Â»â€œ Ã„â€˜Ã¡Â»â€˜i soÃƒÂ¡t, sai sÃ¡Â»â€˜...)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pay_payments"
        db_table_comment = "BÃƒÂºt toÃƒÂ¡n thanh toÃƒÂ¡n Ã¡Â»Å¸ cÃ¡ÂºÂ¥p gateway. Khi succeeded: nÃ¡ÂºÂ¿u lÃƒÂ  nÃ¡ÂºÂ¡p vÃƒÂ­ Ã¢â€ â€™ ghi credit ledger; nÃ¡ÂºÂ¿u lÃƒÂ  order Ã¢â€ â€™ chuyÃ¡Â»Æ’n order sang paid, cÃ¡ÂºÂ¥p license."
        indexes = [
            models.Index(fields=['user', 'created_at'], name='idx_pay_payments_user_created'),
            models.Index(fields=['intent'], name='idx_pay_payments_intent'),
            models.Index(fields=['order'], name='idx_pay_payments_order'),
        ]

    def __str__(self):
        return f"Payment {self.payment_id} - {self.status} - {self.amount}"


class PaySepayWebhookEvent(models.Model):
    """
    Inbox webhook cÃ¡Â»Â§a SePay. Ta luÃƒÂ´n lÃ†Â°u thÃƒÂ´ trÃ†Â°Ã¡Â»â€ºc, sau Ã„â€˜ÃƒÂ³ mÃ¡Â»â€ºi parse vÃƒÂ  xÃ¡Â»Â­ lÃƒÂ½ Ã„â€˜Ã¡Â»Æ’ Ã„â€˜Ã¡ÂºÂ£m bÃ¡ÂºÂ£o an toÃƒÂ n.
    """
    webhook_event_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sepay_tx_id = models.BigIntegerField(
        unique=True,
        db_comment="ID duy nhÃ¡ÂºÂ¥t tÃ¡Â»Â« SePay Ã„â€˜Ã¡Â»Æ’ idempotent (trÃƒÂ¡nh xÃ¡Â»Â­ lÃƒÂ½ trÃƒÂ¹ng)"
    )
    received_at = models.DateTimeField(auto_now_add=True)
    payload = models.JSONField(
        db_comment="LÃ†Â°u nguyÃƒÂªn phÃ¡ÂºÂ§n thÃƒÂ¢n webhook Ã„â€˜Ã¡Â»Æ’ debug/Ã„â€˜Ã¡Â»â€˜i soÃƒÂ¡t"
    )
    processed = models.BooleanField(
        default=False,
        db_comment="Ã„ÂÃƒÂ£ xÃ¡Â»Â­ lÃƒÂ½ phÃƒÂ¡t sinh payment/ledger chÃ†Â°a"
    )
    process_error = models.TextField(
        null=True,
        blank=True,
        db_comment="ThÃƒÂ´ng tin lÃ¡Â»â€”i nÃ¡ÂºÂ¿u xÃ¡Â»Â­ lÃƒÂ½ thÃ¡ÂºÂ¥t bÃ¡ÂºÂ¡i"
    )

    class Meta:
        db_table = "pay_sepay_webhook_events"
        db_table_comment = "Inbox webhook cÃ¡Â»Â§a SePay. Ta luÃƒÂ´n lÃ†Â°u thÃƒÂ´ trÃ†Â°Ã¡Â»â€ºc, sau Ã„â€˜ÃƒÂ³ mÃ¡Â»â€ºi parse vÃƒÂ  xÃ¡Â»Â­ lÃƒÂ½ Ã„â€˜Ã¡Â»Æ’ Ã„â€˜Ã¡ÂºÂ£m bÃ¡ÂºÂ£o an toÃƒÂ n."
        indexes = [
            models.Index(fields=['sepay_tx_id'], name='idx_sepay_webhooks_tx_id'),
            models.Index(fields=['processed'], name='idx_sepay_webhooks_processed'),
            models.Index(fields=['received_at'], name='idx_sepay_webhooks_received'),
        ]

    def __str__(self):
        return f"Webhook {self.webhook_event_id} - TX {self.sepay_tx_id} - Processed: {self.processed}"


class PayBankTransaction(models.Model):
    """
    BÃ¡ÂºÂ£ng Ã„â€˜Ã¡Â»â€˜i soÃƒÂ¡t chÃ¡Â»Â§ Ã„â€˜Ã¡Â»â„¢ng tÃ¡Â»Â« API SePay: id, sÃ¡Â»â€˜ tiÃ¡Â»Ân, nÃ¡Â»â„¢i dung, tham chiÃ¡ÂºÂ¿uÃ¢â‚¬Â¦
    """
    sepay_tx_id = models.BigIntegerField(
        primary_key=True,
        db_comment="KhÃ¡Â»â€ºp vÃ¡Â»â€ºi provider_payment_id khi Ã„â€˜ÃƒÂ£ xÃ¡Â»Â­ lÃƒÂ½"
    )
    transaction_date = models.DateTimeField(
        db_comment="ThÃ¡Â»Âi gian giao dÃ¡Â»â€¹ch ngÃƒÂ¢n hÃƒÂ ng"
    )
    account_number = models.CharField(
        max_length=50,
        db_comment="STK nhÃ¡ÂºÂ­n tiÃ¡Â»Ân"
    )
    amount_in = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal('0.00'),
        db_comment="TiÃ¡Â»Ân vÃƒÂ o (nÃ¡ÂºÂ¡p vÃƒÂ­/ thanh toÃƒÂ¡n)"
    )
    amount_out = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal('0.00'),
        db_comment="TiÃ¡Â»Ân ra (ÃƒÂ­t dÃƒÂ¹ng)"
    )
    content = models.TextField(
        null=True,
        blank=True,
        db_comment="NÃ¡Â»â„¢i dung CK (chÃ¡Â»Â©a order_code Ã„â€˜Ã¡Â»Æ’ auto-match)"
    )
    reference_number = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_comment="MÃƒÂ£ tham chiÃ¡ÂºÂ¿u cÃ¡Â»Â§a ngÃƒÂ¢n hÃƒÂ ng"
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
        db_comment="KhÃ¡Â»â€ºp Ã„â€˜Ã†Â°Ã¡Â»Â£c intent nÃƒÂ o"
    )
    attempt = models.ForeignKey(
        PayPaymentAttempt,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_comment="KhÃ¡Â»â€ºp Ã„â€˜Ã†Â°Ã¡Â»Â£c attempt nÃƒÂ o"
    )
    payment = models.ForeignKey(
        PayPayment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_comment="Payment Ã„â€˜Ã†Â°Ã¡Â»Â£c tÃ¡ÂºÂ¡o/chÃ¡Â»â€˜t tÃ¡Â»Â« giao dÃ¡Â»â€¹ch nÃƒÂ y"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "pay_bank_transactions"
        db_table_comment = "BÃ¡ÂºÂ£ng Ã„â€˜Ã¡Â»â€˜i soÃƒÂ¡t chÃ¡Â»Â§ Ã„â€˜Ã¡Â»â„¢ng tÃ¡Â»Â« API SePay: id, sÃ¡Â»â€˜ tiÃ¡Â»Ân, nÃ¡Â»â„¢i dung, tham chiÃ¡ÂºÂ¿uÃ¢â‚¬Â¦"
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


# ============================================================================
# BOT PURCHASE SYSTEM MODELS
# ============================================================================

class PaySymbolOrder(models.Model):
    """
    Ã„ÂÃ†Â¡n hÃƒÂ ng Ã„â€˜Ã¡Â»Æ’ mua quyÃ¡Â»Ân truy cÃ¡ÂºÂ­p symbol. CÃƒÂ³ thÃ¡Â»Æ’ thanh toÃƒÂ¡n trÃ¡Â»Â±c tiÃ¡ÂºÂ¿p qua SePay hoÃ¡ÂºÂ·c trÃ¡Â»Â« vÃƒÂ­ nÃ¡ÂºÂ¿u Ã„â€˜ÃƒÂ£ nÃ¡ÂºÂ¡p.
    """
    order_id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False,
        db_comment="ID Ã„â€˜Ã†Â¡n hÃƒÂ ng"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_comment="NgÃ†Â°Ã¡Â»Âi mua quyÃ¡Â»Ân truy cÃ¡ÂºÂ­p symbol"
    )
    total_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        db_comment="TÃ¡Â»â€¢ng tiÃ¡Â»Ân cÃ¡ÂºÂ§n trÃ¡ÂºÂ£ cho Ã„â€˜Ã†Â¡n"
    )
    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING_PAYMENT,
        db_comment="TrÃ¡ÂºÂ¡ng thÃƒÂ¡i vÃƒÂ²ng Ã„â€˜Ã¡Â»Âi Ã„â€˜Ã†Â¡n"
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        null=True,
        blank=True,
        db_comment="wallet (trÃ¡Â»Â« vÃƒÂ­) hoÃ¡ÂºÂ·c sepay_transfer (QR/STK)"
    )
    description = models.TextField(
        null=True,
        blank=True,
        db_comment="MÃƒÂ´ tÃ¡ÂºÂ£/ghi chÃƒÂº Ã„â€˜Ã†Â¡n hÃƒÂ ng"
    )
    payment_intent = models.ForeignKey(
        'PayPaymentIntent',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_comment="Payment intent cho SePay transfer"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pay_symbol_orders"
        db_table_comment = "Ã„ÂÃ†Â¡n hÃƒÂ ng Ã„â€˜Ã¡Â»Æ’ mua quyÃ¡Â»Ân truy cÃ¡ÂºÂ­p symbol. CÃƒÂ³ thÃ¡Â»Æ’ thanh toÃƒÂ¡n trÃ¡Â»Â±c tiÃ¡ÂºÂ¿p qua SePay hoÃ¡ÂºÂ·c trÃ¡Â»Â« vÃƒÂ­ nÃ¡ÂºÂ¿u Ã„â€˜ÃƒÂ£ nÃ¡ÂºÂ¡p."
        indexes = [
            models.Index(fields=['user', 'status'], name='idx_symbol_orders_user_status'),
            models.Index(fields=['status'], name='idx_symbol_orders_status'),
            models.Index(fields=['created_at'], name='idx_symbol_orders_created'),
        ]

    def __str__(self):
        return f"Symbol Order {self.order_id} - {self.user.username} - {self.status}"


class PaySymbolOrderItem(models.Model):
    """
    Chi tiÃ¡ÂºÂ¿t tÃ¡Â»Â«ng dÃƒÂ²ng sÃ¡ÂºÂ£n phÃ¡ÂºÂ©m trong Ã„â€˜Ã†Â¡n: symbol nÃƒÂ o, thÃ¡Â»Âi hÃ¡ÂºÂ¡n bao lÃƒÂ¢u.
    """
    order_item_id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False,
        db_comment="ID item Ã„â€˜Ã†Â¡n hÃƒÂ ng"
    )
    order = models.ForeignKey(
        PaySymbolOrder,
        on_delete=models.CASCADE,
        related_name='items',
        db_comment="Ã„ÂÃ†Â¡n hÃƒÂ ng chÃƒÂ­nh"
    )
    symbol_id = models.BigIntegerField(
        db_comment="Symbol lÃƒÂ  sÃ¡ÂºÂ£n phÃ¡ÂºÂ©m Ã„â€˜Ã†Â°Ã¡Â»Â£c bÃƒÂ¡n"
    )
    price = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        db_comment="Ã„ÂÃ†Â¡n giÃƒÂ¡ tÃ¡ÂºÂ¡i thÃ¡Â»Âi Ã„â€˜iÃ¡Â»Æ’m mua"
    )
    license_days = models.IntegerField(
        null=True,
        blank=True,
        db_comment="SÃ¡Â»â€˜ ngÃƒÂ y cÃ¡ÂºÂ¥p quyÃ¡Â»Ân sÃ¡Â»Â­ dÃ¡Â»Â¥ng symbol; null = trÃ¡Â»Ân Ã„â€˜Ã¡Â»Âi"
    )
    auto_renew = models.BooleanField(
        default=False,
        db_comment="Mark this order item as enrolled in auto-renew"
    )
    cycle_days_override = models.PositiveIntegerField(
        null=True,
        blank=True,
        db_comment="Override renewal cycle in days; None uses subscription default"
    )
    auto_renew_price = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
        db_comment="Override price for subsequent renewals; None uses current price"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        db_comment="ThuÃ¡Â»â„¢c tÃƒÂ­nh thÃƒÂªm (phiÃƒÂªn bÃ¡ÂºÂ£n, biÃ¡ÂºÂ¿n thÃ¡Â»Æ’, ...)"
    )

    class Meta:
        db_table = "pay_symbol_order_items"
        db_table_comment = "Chi tiÃ¡ÂºÂ¿t tÃ¡Â»Â«ng dÃƒÂ²ng sÃ¡ÂºÂ£n phÃ¡ÂºÂ©m trong Ã„â€˜Ã†Â¡n: symbol nÃƒÂ o, thÃ¡Â»Âi hÃ¡ÂºÂ¡n bao lÃƒÂ¢u."
        indexes = [
            models.Index(fields=['order'], name='idx_symbol_order_items_order'),
            models.Index(fields=['symbol_id'], name='idx_symbol_order_items_symbol'),
        ]

    def __str__(self):
        return f"Order Item {self.order_item_id} - Symbol {self.symbol_id}"


class PayUserSymbolLicenseManager(models.Manager):
    def create(self, **kwargs):
        is_lifetime = kwargs.pop('is_lifetime', None)
        if is_lifetime is True:
            kwargs['end_at'] = None
        return super().create(**kwargs)


class PayUserSymbolLicense(models.Model):
    """
    QuyÃ¡Â»Ân sÃ¡Â»Â­ dÃ¡Â»Â¥ng symbol Ã„â€˜Ã¡Â»Æ’ quyÃ¡ÂºÂ¿t Ã„â€˜Ã¡Â»â€¹nh ai Ã„â€˜Ã†Â°Ã¡Â»Â£c nhÃ¡ÂºÂ­n tÃƒÂ­n hiÃ¡Â»â€¡u. 
    Gia hÃ¡ÂºÂ¡n bÃ¡ÂºÂ±ng cÃƒÂ¡ch tÃ¡ÂºÂ¡o license mÃ¡Â»â€ºi hoÃ¡ÂºÂ·c cÃ¡ÂºÂ­p nhÃ¡ÂºÂ­t end_at.
    """
    objects = PayUserSymbolLicenseManager()

    def __init__(self, *args, is_lifetime=None, **kwargs):
        if is_lifetime is True:
            kwargs.setdefault('end_at', None)
        super().__init__(*args, **kwargs)

    license_id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False,
        db_comment="ID license"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_comment="User Ã„â€˜Ã†Â°Ã¡Â»Â£c cÃ¡ÂºÂ¥p quyÃ¡Â»Ân"
    )
    symbol_id = models.BigIntegerField(
        db_comment="Symbol Ã„â€˜Ã†Â°Ã¡Â»Â£c cÃ¡ÂºÂ¥p quyÃ¡Â»Ân"
    )
    order = models.ForeignKey(
        PaySymbolOrder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_comment="Ã„ÂÃ†Â¡n hÃƒÂ ng tÃ¡ÂºÂ¡o ra license nÃƒÂ y"
    )
    subscription = models.ForeignKey(
        'setting.SymbolAutoRenewSubscription',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='licenses',
        db_comment="Auto-renew subscription that governs this license"
    )
    status = models.CharField(
        max_length=20,
        choices=LicenseStatus.choices,
        default=LicenseStatus.ACTIVE,
        db_comment="TrÃ¡ÂºÂ¡ng thÃƒÂ¡i quyÃ¡Â»Ân dÃƒÂ¹ng symbol"
    )
    start_at = models.DateTimeField(
        default=timezone.now,
        db_comment="ThÃ¡Â»Âi Ã„â€˜iÃ¡Â»Æ’m kÃƒÂ­ch hoÃ¡ÂºÂ¡t"
    )
    end_at = models.DateTimeField(
        null=True,
        blank=True,
        db_comment="ThÃ¡Â»Âi Ã„â€˜iÃ¡Â»Æ’m hÃ¡ÂºÂ¿t hÃ¡ÂºÂ¡n; null = trÃ¡Â»Ân Ã„â€˜Ã¡Â»Âi"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "pay_user_symbol_licenses"
        db_table_comment = "QuyÃ¡Â»Ân sÃ¡Â»Â­ dÃ¡Â»Â¥ng symbol Ã„â€˜Ã¡Â»Æ’ quyÃ¡ÂºÂ¿t Ã„â€˜Ã¡Â»â€¹nh ai Ã„â€˜Ã†Â°Ã¡Â»Â£c nhÃ¡ÂºÂ­n tÃƒÂ­n hiÃ¡Â»â€¡u."
        indexes = [
            models.Index(fields=['user', 'symbol_id'], name='idx_symbol_lic_user_symbol'),
            models.Index(fields=['status'], name='idx_symbol_lic_status'),
            models.Index(fields=['end_at'], name='idx_symbol_lic_end_at'),
            models.Index(fields=['subscription'], name='idx_symbol_lic_subscription'),
        ]
        unique_together = [('user', 'symbol_id', 'start_at')]

    def __str__(self):
        return f"License {self.license_id} - {self.user.username} - Symbol {self.symbol_id}"

    @property
    def is_active(self):
        """KiÃ¡Â»Æ’m tra license cÃƒÂ³ cÃƒÂ²n hiÃ¡Â»â€¡u lÃ¡Â»Â±c khÃƒÂ´ng"""
        if self.status != LicenseStatus.ACTIVE:
            return False
        if self.end_at and timezone.now() > self.end_at:
            return False
        return True

    @property
    def is_lifetime(self):
        """KiÃ¡Â»Æ’m tra cÃƒÂ³ phÃ¡ÂºÂ£i license trÃ¡Â»Ân Ã„â€˜Ã¡Â»Âi khÃƒÂ´ng"""
        return self.end_at is None



class IntentStatus(models.TextChoices):
    PENDING = 'requires_payment_method', 'Pending'
    PROCESSING = 'processing', 'Processing'
    COMPLETED = 'succeeded', 'Completed'
    FAILED = 'failed', 'Failed'
    EXPIRED = 'expired', 'Expired'

# Backwards compatibility alias for legacy imports
PaySymbolLicense = PayUserSymbolLicense



