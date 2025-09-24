import uuid
from typing import Optional, Dict, Any
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from ninja.errors import HttpError
from typing import List
from apps.seapay.repositories.payment_repository import PaymentRepository
from apps.seapay.models import PayWallet, PayPaymentIntent, IntentPurpose

User = get_user_model()


class PaymentService:
    """Service layer cho payment business logic"""
    
    def __init__(self):
        self.repository = PaymentRepository()
    
    def create_payment_intent(
        self,
        user: User,
        purpose: str,
        amount: Decimal,
        currency: str = "VND",
        expires_in_minutes: int = 60,
        return_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
        metadata: Dict[str, Any] = None
    ) -> PayPaymentIntent:
        """Tạo payment intent mới"""
        
        valid_purposes = ['wallet_topup', 'order_payment', 'withdraw']
        if purpose not in valid_purposes:
            raise HttpError(400, f"Invalid purpose. Must be one of: {valid_purposes}")
        
        if amount <= 0:
            raise HttpError(400, "Amount must be greater than 0")
        
        wallet, _ = self.repository.get_or_create_wallet(user, currency)
        
        if not wallet.is_active:
            raise HttpError(400, "Wallet is suspended")
        
        order_code = f"PAY_{uuid.uuid4().hex[:8].upper()}_{int(timezone.now().timestamp())}"
        
        # Tính expires_at
        expires_at = timezone.now() + timedelta(minutes=expires_in_minutes)
        
        # Tạo payment intent
        intent = self.repository.create_payment_intent(
            user=user,
            wallet=wallet,
            provider='sepay',
            purpose=purpose,
            amount=amount,
            order_code=order_code,
            expires_at=expires_at,
            return_url=return_url,
            cancel_url=cancel_url,
            metadata=metadata or {}
        )
        
        return intent
    
    def generate_qr_code_url(self, order_code: str, amount: Decimal) -> str:
        """Sinh QR code URL cho payment"""
        return (
            f"https://qr.sepay.vn/img?acc=96247CISI1"
            f"&bank=BIDV"
            f"&amount={int(amount)}"
            f"&des={order_code}"
            f"&template=compact"
        )
    
    def process_callback(
        self,
        content: str,
        amount: Decimal,
        transfer_type: str,
        reference_code: str
    ) -> Dict[str, Any]:
        """Xử lý callback từ SeaPay"""
        
        if not content:
            raise HttpError(400, "Missing content (order_code)")
        
        if transfer_type != "in":
            return {"message": "Ignored - not an incoming transfer", "transfer_type": transfer_type}
        
        intent = self._find_payment_intent_by_order_code(content)
        
        if not intent:
            raise HttpError(404, f"Payment intent not found for order_code: {content}")
        
        if amount != intent.amount:
            # Special handling for wallet topup - allow partial payments
            if intent.purpose == IntentPurpose.WALLET_TOPUP and amount > 0:
                print(f"⚠️ Partial topup detected. Expected: {intent.amount}, Received: {amount}")
                # Process partial amount for wallet topup
                return self._process_partial_wallet_topup(intent, amount, {
                    'content': content,
                    'amount': amount,
                    'transfer_type': transfer_type,
                    'reference_code': reference_code
                })
            else:
                raise HttpError(400, f"Amount mismatch. Expected: {intent.amount}, Received: {amount}")
        
        if intent.status not in ['requires_payment_method', 'pending_payment']:
            # Intent đã processed, nhưng vẫn cần check order status
            if intent.status == 'succeeded' and intent.purpose == 'order_payment':
                self._ensure_order_status_synced(intent)
            return {"message": "Already processed", "intent_id": str(intent.intent_id), "status": intent.status}
        
        if intent.is_expired:
            self.repository.update_payment_intent_status(intent, 'expired')
            raise HttpError(400, "Payment intent has expired")
        
        return self._process_successful_payment(intent, reference_code)
    
    def _find_payment_intent_by_order_code(self, content: str) -> Optional[PayPaymentIntent]:
        """Tìm payment intent với order code normalization"""
        intent = self.repository.get_payment_intent_by_order_code(content)
        
        if not intent and content.startswith("PAY") and len(content) > 11:
            formatted_content = f"PAY_{content[3:11]}_{content[11:]}"
            intent = self.repository.get_payment_intent_by_order_code(formatted_content)
            
            if intent:
                print(f"Found intent using formatted order code: {formatted_content} (original: {content})")
        
        return intent
    
    def _process_successful_payment(self, intent: PayPaymentIntent, reference_code: str) -> Dict[str, Any]:
        """Xử lý payment thành công"""
        self.repository.update_payment_intent_status(intent, 'succeeded', reference_code)
        
        if intent.purpose == 'wallet_topup':
            if intent.wallet:
                self.repository.update_wallet_balance(intent.wallet, intent.amount)
                print(f"Updated wallet {intent.wallet.id} balance: +{intent.amount}, new balance: {intent.wallet.balance}")
        
        elif intent.purpose == 'order_payment':
            # Xử lý thanh toán đơn hàng symbol
            self._process_symbol_order_payment(intent)
            
        elif intent.purpose == 'withdraw':
            # Xử lý rút tiền
            pass
        
        # Get wallet balance if available
        wallet_balance = None
        if hasattr(intent, 'wallet') and intent.wallet:
            wallet_balance = float(intent.wallet.balance)
        elif intent.user:
            user_wallet = self.repository.get_wallet_by_user(intent.user)
            if user_wallet:
                wallet_balance = float(user_wallet.balance)
        
        return {
            "message": "OK", 
            "intent_id": str(intent.intent_id),
            "order_code": intent.order_code,
            "status": intent.status,
            "wallet_balance": wallet_balance
        }
    
    def _process_symbol_order_payment(self, intent: PayPaymentIntent) -> None:
        """Xử lý thanh toán đơn hàng symbol thành công"""
        from apps.seapay.models import PaySymbolOrder
        
        try:
            # Tìm symbol order dựa trên payment intent
            order = PaySymbolOrder.objects.filter(
                payment_intent_id=intent.intent_id
            ).first()
            
            if order:
                order.status = 'paid'
                order.save(update_fields=['status', 'updated_at'])
                
                self._create_symbol_licenses(order)
                
                print(f"✅ Symbol order {order.order_id} marked as paid and licenses created")
            else:
                print(f"⚠️ No symbol order found for payment intent {intent.intent_id}")
                
        except Exception as e:
            print(f"❌ Error processing symbol order payment: {e}")
    
    def _create_symbol_licenses(self, order) -> None:
        """Tạo licenses cho symbol order"""
        from apps.seapay.models import PayUserSymbolLicense
        from django.utils import timezone
        import uuid
        
        for item in order.items.all():
            # Calculate end date
            license_days = item.license_days or 30
            end_at = timezone.now() + timezone.timedelta(days=license_days)
            
            user_license = PayUserSymbolLicense.objects.create(
                license_id=uuid.uuid4(),
                user=order.user,
                symbol_id=item.symbol_id,
                order=order,
                end_at=end_at
            )
            print(f"✅ Created license {user_license.license_id} for symbol {item.symbol_id} (expires: {end_at})")
    
    def _ensure_order_status_synced(self, intent: PayPaymentIntent) -> None:
        """Đảm bảo order status sync với intent status"""
        from apps.seapay.models import PaySymbolOrder
        
        try:
            order = PaySymbolOrder.objects.filter(
                payment_intent_id=intent.intent_id
            ).first()
            
            if order and order.status == 'pending_payment':
                print(f"🔄 Syncing order {order.order_id} status with succeeded intent")
                self._process_symbol_order_payment(intent)
            elif order:
                print(f"ℹ️ Order {order.order_id} already has status: {order.status}")
            else:
                print(f"⚠️ No order found for intent {intent.intent_id}")
                
        except Exception as e:
            print(f"❌ Error syncing order status: {e}")
    
    def get_payment_intent(self, intent_id: str, user) -> PayPaymentIntent:
        """Lấy payment intent theo ID"""
        intent = self.repository.get_payment_intent_by_id(intent_id, user)
        if not intent:
            raise HttpError(404, "Payment intent not found")
        return intent
    
    def get_or_create_wallet(self, user: User) -> PayWallet:
        """Lấy hoặc tạo wallet cho user"""
        wallet = self.repository.get_wallet_by_user(user)
        if not wallet:
            wallet, _ = self.repository.get_or_create_wallet(user)
        return wallet
    
    def create_legacy_order(self, order_id: str, amount: Decimal, description: str = "") -> Dict[str, Any]:
        """Tạo legacy order (cho compatibility)"""
        order, created = self.repository.get_or_create_legacy_order(order_id, amount, description)
        
        if not created:
            raise HttpError(400, f"Order {order_id} already exists")
        
        transfer_content = f"SEAPAY_{order_id}"
        
        qr_code_url = self.generate_qr_code_url(transfer_content, amount)
        
        return {
            "order_id": str(order.id),
            "qr_code_url": qr_code_url,
            "transfer_content": transfer_content,
            "status": order.status
        }
        
    def get_user_wallet(self, user: User) -> PayWallet:
        """Lấy wallet của user"""
        wallet, _ = self.repository.get_or_create_wallet(user)
        return wallet
        
    def list_user_payment_intents(self, user: User) -> List[PayPaymentIntent]:
        """Lấy tất cả payment intents của user"""
        return self.repository.get_payment_intents_by_user(user)    
        
    def get_paginated_payment_intents(
        self,
        user: User,
        page: int = 1,
        limit: int = 10,
        search: Optional[str] = None,
        status: Optional[str] = None,
        purpose: Optional[str] = None,
    ):
        """Lấy payment intents với phân trang"""
        page = page or 1
        limit = limit or 10
        total, items = self.repository.get_payment_intents_by_user(
            user, page, limit, search, status, purpose
        )
        return {
            "total": total,
            "results": items,
            "page": page,
            "page_size": limit,  
        }
    
    def _process_partial_wallet_topup(self, intent: PayPaymentIntent, amount: Decimal, transaction_data: Dict) -> Dict[str, Any]:
        """Xử lý partial wallet topup - tạo topup độc lập với số tiền thực tế"""
        try:
            # Import services cần thiết
            from apps.seapay.models import PayWallet, PayWalletLedger, PayBankTransaction, PayPayment, WalletTxType, PaymentStatus
            from django.db import transaction
            import random
            
            # Lấy user từ intent
            user = intent.user
            
            # Lấy hoặc tạo wallet
            wallet, _ = PayWallet.objects.get_or_create(
                user=user,
                defaults={'currency': 'VND', 'balance': Decimal('0.00'), 'status': 'active'}
            )
            
            with transaction.atomic():
                # Tạo fake sepay transaction ID
                fake_sepay_id = random.randint(90000000, 99999999)
                
                # Tạo bank transaction record
                bank_tx = PayBankTransaction.objects.create(
                    sepay_tx_id=fake_sepay_id,
                    transaction_date=timezone.now(),
                    account_number='1160976779',
                    amount_in=amount,
                    amount_out=Decimal('0.00'),
                    content=f"PARTIAL_TOPUP_{fake_sepay_id}",
                    reference_number=transaction_data.get('reference_code', ''),
                    bank_code='BIDV'
                )
                
                # Tạo payment record
                payment = PayPayment.objects.create(
                    user=user,
                    order=None,  # Không liên kết với order cụ thể
                    intent=None,  # Không liên kết với intent cũ
                    amount=amount,
                    status=PaymentStatus.SUCCEEDED,
                    provider_payment_id=str(fake_sepay_id),
                    message=f"Partial wallet topup: {amount} VND",
                    metadata={
                        'original_intent_id': str(intent.intent_id),
                        'original_expected_amount': float(intent.amount),
                        'partial_topup': True,
                        'bank_transaction_id': fake_sepay_id
                    }
                )
                
                # Tạo ledger entry
                balance_before = wallet.balance
                balance_after = balance_before + amount
                
                ledger_entry = PayWalletLedger.objects.create(
                    wallet=wallet,
                    tx_type=WalletTxType.DEPOSIT,
                    amount=amount,
                    is_credit=True,
                    balance_before=balance_before,
                    balance_after=balance_after,
                    payment=payment,
                    note=f"Partial topup from bank transfer - {amount} VND"
                )
                
                # Cập nhật wallet balance
                wallet.balance = balance_after
                wallet.save(update_fields=['balance', 'updated_at'])
            
            return {
                "message": f"Partial topup processed: {amount} VND added to wallet", 
                "intent_id": str(intent.intent_id),
                "amount_processed": float(amount),
                "amount_expected": float(intent.amount),
                "remaining_amount": float(intent.amount - amount),
                "new_wallet_balance": float(wallet.balance),
                "payment_id": str(payment.payment_id),
                "status": "partial_success"
            }
            
        except Exception as e:
            print(f"Error processing partial topup: {e}")
            import traceback
            traceback.print_exc()
            return {
                "message": f"Partial topup failed: {str(e)}", 
                "intent_id": str(intent.intent_id),
                "status": "partial_failed"
            }