import uuid
import secrets
from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model

from apps.seapay.models import (
    PayWallet, PayPaymentIntent, PayPaymentAttempt, PayPayment, 
    PayBankTransaction, PaySepayWebhookEvent, PayWalletLedger,
    IntentPurpose, PaymentStatus
)
from apps.seapay.services.sepay_client import SepayClient
from apps.seapay.repositories.payment_repository import PaymentRepository

User = get_user_model()


class WalletTopupService:
    """Service Ä‘á»ƒ xá»­ lÃ½ luá»“ng náº¡p tiá»n vÃ­ hoÃ n chá»‰nh"""
    
    def __init__(self):
        self.sepay_client = SepayClient()
        self.repository = PaymentRepository()
    
    def create_topup_intent(
        self, 
        user, 
        amount: Decimal, 
        currency: str = "VND",
        expires_in_minutes: int = 60,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PayPaymentIntent:
        """
        BÆ°á»›c 1: Táº¡o payment intent cho náº¡p vÃ­
        """
        if amount <= 0:
            raise ValueError("Amount must be greater than 0")
        
        # Láº¥y hoáº·c táº¡o vÃ­ cho user
        wallet, _ = self._get_or_create_wallet(user, currency)
        
        if not wallet.is_active:
            raise ValueError("Wallet is suspended")
        
        # Táº¡o order_code duy nháº¥t cho Ä‘á»‘i soÃ¡t
        order_code = self._generate_order_code()
        
        # TÃ­nh thá»i gian háº¿t háº¡n
        expires_at = timezone.now() + timedelta(minutes=expires_in_minutes)
        
        # Táº¡o intent
        with transaction.atomic():
            intent = PayPaymentIntent.objects.create(
                user=user,
                order=None,  # Wallet topup khÃ´ng cÃ³ order
                purpose=IntentPurpose.WALLET_TOPUP,
                amount=amount,
                status=PaymentStatus.REQUIRES_PAYMENT_METHOD,
                order_code=order_code,
                expires_at=expires_at,
                metadata=metadata or {}
            )
        
        return intent
    
    def create_payment_attempt(
        self, 
        intent: PayPaymentIntent,
        bank_code: str = "BIDV"
    ) -> PayPaymentAttempt:
        """
        BÆ°á»›c 2: Táº¡o attempt vÃ  sinh QR code
        """
        if intent.purpose != IntentPurpose.WALLET_TOPUP:
            raise ValueError("Intent is not for wallet topup")
        
        if intent.is_expired():
            raise ValueError("Intent has expired")
        
        if intent.status != PaymentStatus.REQUIRES_PAYMENT_METHOD:
            raise ValueError("Intent is not in correct status for creating attempt")
        
        # Táº¡o QR code qua SePay
        qr_data = self.sepay_client.create_qr_code(
            amount=intent.amount,
            content=intent.order_code,
            bank_code=bank_code
        )
        
        # Táº¡o attempt
        with transaction.atomic():
            attempt = PayPaymentAttempt.objects.create(
                intent=intent,
                status=PaymentStatus.REQUIRES_PAYMENT_METHOD,
                bank_code=bank_code,
                account_number=qr_data.get('account_number'),
                account_name=qr_data.get('account_name'),
                transfer_content=intent.order_code,
                transfer_amount=intent.amount,
                qr_image_url=qr_data.get('qr_image_url'),
                qr_svg=qr_data.get('qr_svg'),
                provider_session_id=qr_data.get('session_id'),
                expires_at=intent.expires_at,
                metadata={
                    'bank_code': bank_code,
                    'qr_created_at': timezone.now().isoformat()
                }
            )
            
            # Cáº­p nháº­t intent status
            intent.status = PaymentStatus.PROCESSING
            intent.save(update_fields=['status', 'updated_at'])
        
        return attempt
    
    def process_webhook_event(self, webhook_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        BÆ°á»›c 3: Xá»­ lÃ½ webhook tá»« SePay
        """
        sepay_tx_id = webhook_payload.get('id')
        if not sepay_tx_id:
            raise ValueError("Missing sepay transaction id in webhook")
        
        # LÆ°u webhook event thÃ´ trÆ°á»›c
        webhook_event = self._store_webhook_event(sepay_tx_id, webhook_payload)
        
        try:
            # Xá»­ lÃ½ webhook
            result = self._process_webhook_data(webhook_payload)
            
            # ÄÃ¡nh dáº¥u Ä‘Ã£ xá»­ lÃ½ thÃ nh cÃ´ng
            webhook_event.processed = True
            webhook_event.save(update_fields=['processed'])
            
            return result
            
        except Exception as e:
            # LÆ°u lá»—i Ä‘á»ƒ debug
            webhook_event.process_error = str(e)
            webhook_event.save(update_fields=['process_error'])
            raise
    
    def reconcile_bank_transaction(
        self, 
        sepay_tx_id: int,
        transaction_data: Dict[str, Any]
    ) -> Optional[PayPayment]:
        """
        BÆ°á»›c 4: Äá»‘i soÃ¡t vÃ  táº¡o payment
        """
        # LÆ°u bank transaction
        bank_tx = self._store_bank_transaction(sepay_tx_id, transaction_data)
        
        # TÃ¬m intent dá»±a trÃªn content
        content = transaction_data.get('content', '')
        intent = self._find_intent_by_content(content)
        
        if not intent:
            # KhÃ´ng tÃ¬m tháº¥y intent phÃ¹ há»£p
            return None
        
        # Kiá»ƒm tra sá»‘ tiá»n
        amount = Decimal(str(transaction_data.get('transferAmount', 0)))
        if amount != intent.amount:
            print(f"Amount mismatch for intent {intent.intent_id}: expected {intent.amount}, got {amount}")
            return None
        
        # Táº¡o payment
        payment = self._create_payment(intent, bank_tx, amount)
        
        # Cáº­p nháº­t liÃªn káº¿t
        bank_tx.intent = intent
        bank_tx.payment = payment
        bank_tx.save(update_fields=['intent', 'payment'])
        
        return payment
    
    def finalize_topup(self, payment: PayPayment) -> PayWalletLedger:
        """
        BÆ°á»›c 5: Chá»‘t thanh toÃ¡n vÃ  ghi ledger
        """
        if payment.status != PaymentStatus.SUCCEEDED:
            raise ValueError("Payment is not in succeeded status")
        
        intent = payment.intent
        if not intent or intent.purpose != IntentPurpose.WALLET_TOPUP:
            raise ValueError("Invalid payment intent for wallet topup")
        
        # Láº¥y vÃ­ cá»§a user
        wallet = self._get_or_create_wallet(payment.user)[0]
        
        # Ghi ledger vÃ  cáº­p nháº­t sá»‘ dÆ°
        with transaction.atomic():
            ledger_entry = self._create_ledger_entry(
                wallet=wallet,
                tx_type='deposit',
                amount=payment.amount,
                is_credit=True,
                payment=payment,
                description=f"Wallet topup via SePay - {payment.provider_payment_id}"
            )
            
            # Cáº­p nháº­t cache sá»‘ dÆ° trong wallet
            wallet.balance = ledger_entry.balance_after
            wallet.save(update_fields=['balance', 'updated_at'])
            
            # Cáº­p nháº­t intent status
            intent.status = PaymentStatus.SUCCEEDED
            intent.save(update_fields=['status', 'updated_at'])
        
        return ledger_entry
    
    def get_topup_status(self, intent_id: str, user) -> Dict[str, Any]:
        """Láº¥y tráº¡ng thÃ¡i náº¡p tiá»n"""
        try:
            intent = PayPaymentIntent.objects.get(
                intent_id=intent_id, 
                user=user,
                purpose=IntentPurpose.WALLET_TOPUP
            )
        except PayPaymentIntent.DoesNotExist:
            raise ValueError("Topup intent not found")
        
        # Láº¥y attempt má»›i nháº¥t
        latest_attempt = intent.paypaymentattempt_set.order_by('-created_at').first()
        
        # Láº¥y payment náº¿u cÃ³
        payment = intent.paypayment_set.filter(status=PaymentStatus.SUCCEEDED).first()
        
        # Láº¥y ledger entry náº¿u cÃ³
        ledger_entry = None
        if payment:
            ledger_entry = payment.ledger_entries.first()
        
        return {
            'intent': {
                'id': str(intent.intent_id),
                'amount': intent.amount,
                'status': intent.status,
                'order_code': intent.order_code,
                'expires_at': intent.expires_at.isoformat() if intent.expires_at else None,
                'is_expired': intent.is_expired(),
                'created_at': intent.created_at.isoformat()
            },
            'attempt': {
                'id': str(latest_attempt.attempt_id),
                'qr_image_url': latest_attempt.qr_image_url,
                'account_number': latest_attempt.account_number,
                'account_name': latest_attempt.account_name,
                'transfer_content': latest_attempt.transfer_content,
                'transfer_amount': latest_attempt.transfer_amount,
                'bank_code': latest_attempt.bank_code
            } if latest_attempt else None,
            'payment': {
                'id': str(payment.payment_id),
                'amount': payment.amount,
                'status': payment.status,
                'provider_payment_id': payment.provider_payment_id,
                'created_at': payment.created_at.isoformat()
            } if payment else None,
            'ledger': {
                'id': str(ledger_entry.ledger_id),
                'balance_before': ledger_entry.balance_before,
                'balance_after': ledger_entry.balance_after,
                'created_at': ledger_entry.created_at.isoformat()
            } if ledger_entry else None
        }
    
    # Private helper methods
    
    def _get_or_create_wallet(self, user, currency: str = "VND"):
        """Láº¥y hoáº·c táº¡o vÃ­ cho user"""
        return PayWallet.objects.get_or_create(
            user=user,
            defaults={
                'currency': currency,
                'balance': Decimal('0.00'),
                'status': 'active'
            }
        )
    
    def _generate_order_code(self) -> str:
        """Sinh order_code duy nháº¥t - format phÃ¹ há»£p vá»›i SePay"""
        timestamp = int(timezone.now().timestamp())
        random_suffix = secrets.token_hex(4).upper()
        return f"TOPUP{timestamp}{random_suffix}"
    
    def _store_webhook_event(self, sepay_tx_id: int, payload: Dict[str, Any]) -> PaySepayWebhookEvent:
        """LÆ°u webhook event thÃ´"""
        webhook_event, _ = PaySepayWebhookEvent.objects.get_or_create(
            sepay_tx_id=sepay_tx_id,
            defaults={
                'payload': payload,
                'processed': False
            }
        )
        return webhook_event
    
    def _process_webhook_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Xá»­ lÃ½ dá»¯ liá»‡u webhook"""
        # Extract transaction info
        sepay_tx_id = payload.get('id')
        
        # TÃ¬m vÃ  xá»­ lÃ½ transaction
        result = self.reconcile_bank_transaction(sepay_tx_id, payload)
        
        if result:
            # Chá»‘t thanh toÃ¡n
            self.finalize_topup(result)
            return {
                'status': 'success',
                'payment_id': str(result.payment_id),
                'message': 'Topup completed successfully'
            }
        else:
            return {
                'status': 'no_match',
                'message': 'No matching intent found for this transaction'
            }
    
    def _store_bank_transaction(self, sepay_tx_id: int, data: Dict[str, Any]) -> PayBankTransaction:
        """LÆ°u bank transaction data"""
        bank_tx, _ = PayBankTransaction.objects.get_or_create(
            sepay_tx_id=sepay_tx_id,
            defaults={
                'transaction_date': timezone.now(),
                'account_number': data.get('accountNumber', ''),
                'amount_in': Decimal(str(data.get('transferAmount', 0))),
                'amount_out': Decimal('0.00'),
                'content': data.get('content', ''),
                'reference_number': data.get('referenceCode', ''),
                'bank_code': data.get('gateway', '')
            }
        )
        return bank_tx
    
    def _find_intent_by_content(self, content: str) -> Optional[PayPaymentIntent]:
        """TÃ¬m intent dá»±a trÃªn content - xá»­ lÃ½ cáº£ format cÃ³ vÃ  khÃ´ng cÃ³ dáº¥u gáº¡ch dÆ°á»›i"""
        try:
            # Thá»­ tÃ¬m vá»›i order_code y há»‡t
            return PayPaymentIntent.objects.get(
                order_code=content,
                purpose=IntentPurpose.WALLET_TOPUP,
                status__in=[PaymentStatus.REQUIRES_PAYMENT_METHOD, PaymentStatus.PROCESSING]
            )
        except PayPaymentIntent.DoesNotExist:
            # Thá»­ tÃ¬m vá»›i format cÃ³ dáº¥u gáº¡ch dÆ°á»›i (backward compatibility)
            if content.startswith('TOPUP') and '_' not in content:
                # Convert TOPUP175851230913D20160 -> TOPUP_1758512309_13D20160
                # Giáº£ sá»­ timestamp lÃ  10 chá»¯ sá»‘, random lÃ  pháº§n cÃ²n láº¡i
                if len(content) > 15:  # TOPUP + 10 timestamp + random
                    timestamp_part = content[5:15]  # Láº¥y 10 chá»¯ sá»‘ sau TOPUP
                    random_part = content[15:]       # Pháº§n cÃ²n láº¡i
                    legacy_format = f"TOPUP_{timestamp_part}_{random_part}"
                    
                    try:
                        return PayPaymentIntent.objects.get(
                            order_code=legacy_format,
                            purpose=IntentPurpose.WALLET_TOPUP,
                            status__in=[PaymentStatus.REQUIRES_PAYMENT_METHOD, PaymentStatus.PROCESSING]
                        )
                    except PayPaymentIntent.DoesNotExist:
                        pass
            
            return None
    
    def _create_payment(self, intent: PayPaymentIntent, bank_tx: PayBankTransaction, amount: Decimal) -> PayPayment:
        """Táº¡o payment record"""
        payment = PayPayment.objects.create(
            user=intent.user,
            order=None, 
            intent=intent,
            amount=amount,
            status=PaymentStatus.SUCCEEDED,
            provider_payment_id=str(bank_tx.sepay_tx_id),
            message="Wallet topup via SePay",
            metadata={
                'bank_transaction_id': bank_tx.sepay_tx_id,
                'reconciliation_time': timezone.now().isoformat()
            }
        )
        return payment
    
    def _create_ledger_entry(
        self, 
        wallet: PayWallet, 
        tx_type: str, 
        amount: Decimal, 
        is_credit: bool,
        payment: PayPayment = None,
        description: str = ""
    ) -> PayWalletLedger:
        """Táº¡o ledger entry vÃ  tÃ­nh sá»‘ dÆ° má»›i"""
        balance_before = wallet.balance
        
        if is_credit:
            balance_after = balance_before + amount
        else:
            balance_after = balance_before - amount
            
        if balance_after < 0:
            raise ValueError("Insufficient wallet balance")
        
        ledger_entry = PayWalletLedger.objects.create(
            wallet=wallet,
            tx_type=tx_type,
            amount=amount,
            is_credit=is_credit,
            balance_before=balance_before,
            balance_after=balance_after,
            payment=payment,
            note=description,
            metadata={}
        )
        
        return ledger_entry
