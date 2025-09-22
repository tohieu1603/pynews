from ninja import Schema
from decimal import Decimal
from typing import Optional, List
from datetime import datetime


# User DTOs
class UserResponse(Schema):
    id: int
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool
    date_joined: datetime


# Request DTOs
class CreatePaymentIntentRequest(Schema):
    purpose: str 
    amount: Decimal
    currency: str = "VND"
    return_url: Optional[str] = None
    cancel_url: Optional[str] = None
    expires_in_minutes: int = 60
    metadata: dict = {}


class PaymentCallbackRequest(Schema):
    gateway: str
    transactionDate: str
    accountNumber: str
    subAccount: str
    code: Optional[str] = None
    content: str 
    transferType: str
    description: str
    transferAmount: Decimal
    referenceCode: str
    accumulated: int
    id: int


class CreateLegacyOrderRequest(Schema):
    order_id: str
    amount: Decimal
    description: str = ""


class CreatePaymentIntentResponse(Schema):
    intent_id: str
    order_code: str
    qr_code_url: str
    transfer_content: str
    amount: Decimal
    status: str
    expires_at: str


class PaymentIntentDetailResponse(Schema):
    intent_id: str
    order_code: str
    amount: float
    status: str
    purpose: str
    expires_at: Optional[str]
    is_expired: bool
    created_at: str
    updated_at: str


class WalletResponse(Schema):
    wallet_id: str
    balance: float
    currency: str
    status: str
    created_at: str
    updated_at: str


class PaymentCallbackResponse(Schema):
    message: str
    intent_id: Optional[str] = None
    order_code: Optional[str] = None
    status: Optional[str] = None
    wallet_balance: Optional[float] = None
    transfer_type: Optional[str] = None


class CreateLegacyOrderResponse(Schema):
    order_id: str
    qr_code_url: str
    transfer_content: str
    status: str


class FallbackCallbackResponse(Schema):
    message: str
    path: str
    method: Optional[str] = None
    params: Optional[dict] = None

class PaymentIntentOut(Schema):
    id: str
    order_code: str
    reference_code: Optional[str]
    amount: Decimal
    status: str
    purpose: str
    provider: str
    created_at: datetime
    user_id: int 


class PaginatedPaymentIntent(Schema):
    total: int
    page: int
    page_size: int
    user: UserResponse  
    results: List[PaymentIntentOut]