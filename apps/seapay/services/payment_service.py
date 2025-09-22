import uuid
from typing import Optional, Dict, Any
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from ninja.errors import HttpError
from typing import List
from apps.seapay.repositories.payment_repository import PaymentRepository
from apps.seapay.models import PayWallet, PayPaymentIntent

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
            raise HttpError(400, f"Amount mismatch. Expected: {intent.amount}, Received: {amount}")
        
        if intent.status != 'requires_payment_method':
            return {"message": "Already processed", "intent_id": str(intent.id), "status": intent.status}
        
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
            self.repository.update_wallet_balance(intent.wallet, intent.amount)
            print(f"Updated wallet {intent.wallet.id} balance: +{intent.amount}, new balance: {intent.wallet.balance}")
        
        # TODO: Xử lý các purpose khác
        elif intent.purpose == 'order_payment':
            # Xử lý thanh toán đơn hàng
            pass
        elif intent.purpose == 'withdraw':
            # Xử lý rút tiền
            pass
        
        return {
            "message": "OK", 
            "intent_id": str(intent.id),
            "order_code": intent.order_code,
            "status": intent.status,
            "wallet_balance": float(intent.wallet.balance) if intent.wallet else None
        }
    
    def get_payment_intent(self, intent_id: str, user: User) -> PayPaymentIntent:
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