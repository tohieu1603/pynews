import json
from ninja import Router
from ninja.errors import HttpError
from django.http import HttpRequest
from core.jwt_auth import JWTAuth

from apps.seapay.services.payment_service import PaymentService
from apps.seapay.schemas import (
    CreatePaymentIntentRequest,
    CreatePaymentIntentResponse,
    PaymentIntentDetailResponse,
    WalletResponse,
    PaymentCallbackResponse,
    CreateLegacyOrderRequest,
    CreateLegacyOrderResponse,
    FallbackCallbackResponse,
    PaymentIntentOut,
    PaginatedPaymentIntent,
    UserResponse,  # Added UserResponse import
)

router = Router()
payment_service = PaymentService()


@router.post("/create-intent", response=CreatePaymentIntentResponse, auth=JWTAuth())
def create_payment_intent(request: HttpRequest, data: CreatePaymentIntentRequest):
    user = request.auth
    
    intent = payment_service.create_payment_intent(
        user=user,
        purpose=data.purpose,
        amount=data.amount,
        currency=data.currency,
        expires_in_minutes=data.expires_in_minutes,
        return_url=data.return_url,
        cancel_url=data.cancel_url,
        metadata=data.metadata
    )
    
    qr_code_url = payment_service.generate_qr_code_url(intent.order_code, intent.amount)
    
    return CreatePaymentIntentResponse(
        intent_id=str(intent.id),
        order_code=intent.order_code,
        qr_code_url=qr_code_url,
        transfer_content=intent.order_code,
        amount=intent.amount,
        status=intent.status,
        expires_at=intent.expires_at.isoformat()
    )


@router.post("/callback")
@router.get("/callback")
def seapay_callback(request: HttpRequest):

    try:
        data = json.loads(request.body)
        print("SePay callback data:", data)
    except Exception as e:
        print(f"JSON parsing error: {e}")
        try:
            data = dict(request.POST)
            print(f"Form data: {data}")
        except Exception:
            return PaymentCallbackResponse(
                message="Could not parse request data"
            )
    
    result = payment_service.process_callback(
        content=data.get("content", "").strip(),
        amount=data.get("transferAmount", 0),
        transfer_type=data.get("transferType", ""),
        reference_code=data.get("referenceCode", "")
    )
    
    return PaymentCallbackResponse(**result)


@router.get("/intent/{intent_id}", response=PaymentIntentDetailResponse, auth=JWTAuth())
def get_payment_intent(request: HttpRequest, intent_id: str):
    """Lấy thông tin payment intent"""
    user = request.auth
    
    intent = payment_service.get_payment_intent(intent_id, user)
    
    return PaymentIntentDetailResponse(
        intent_id=str(intent.id),
        order_code=intent.order_code,
        amount=float(intent.amount),
        status=intent.status,
        purpose=intent.purpose,
        expires_at=intent.expires_at.isoformat() if intent.expires_at else None,
        is_expired=intent.is_expired,
        created_at=intent.created_at.isoformat(),
        updated_at=intent.updated_at.isoformat()
    )


@router.get("/wallet", response=WalletResponse, auth=JWTAuth())
def get_wallet(request: HttpRequest):
    """Lấy thông tin wallet của user"""
    user = request.auth
    
    wallet = payment_service.get_or_create_wallet(user)
    
    return WalletResponse(
        wallet_id=str(wallet.id),
        balance=float(wallet.balance),
        currency=wallet.currency,
        status=wallet.status,
        created_at=wallet.created_at.isoformat(),
        updated_at=wallet.updated_at.isoformat()
    )

@router.post("/create", response=CreateLegacyOrderResponse)
def create_order(request: HttpRequest, data: CreateLegacyOrderRequest):
    """Legacy API - use /create-intent instead"""
    result = payment_service.create_legacy_order(
        order_id=data.order_id,
        amount=data.amount,
        description=data.description
    )
    
    return CreateLegacyOrderResponse(**result)

@router.get('/wallet', response=WalletResponse, auth=JWTAuth())
def get_wallet(request: HttpRequest):
    """Lấy thông tin wallet của user"""
    user = request.auth
    wallet = payment_service.get_user_wallet(user)
    return WalletResponse(
        wallet_id=str(wallet.id),
        balance=float(wallet.balance),
        currency=wallet.currency,
        status=wallet.status,
        created_at=wallet.created_at.isoformat(),
        updated_at=wallet.updated_at.isoformat()
    )

@router.get("/payments/user", response=PaginatedPaymentIntent, auth=JWTAuth())
def list_user_payments(
    request: HttpRequest,
    page: int = 1,
    limit: int = 10,
    search: str | None = None,
    status: str | None = None,
    purpose: str | None = None,
):
    """
    Lấy tất cả payment intents của user với phân trang + tìm kiếm + lọc
    """
    user = request.auth
    result = payment_service.get_paginated_payment_intents(
        user=user,
        page=page,
        limit=limit,
        search=search,
        status=status,
        purpose=purpose,
    )

    return PaginatedPaymentIntent(
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        user=UserResponse(  # User info ở top level
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            is_active=user.is_active,
            date_joined=user.date_joined,
        ),
        results=[
            PaymentIntentOut(
                id=str(intent.id),
                order_code=intent.order_code,
                reference_code=intent.reference_code,
                amount=intent.amount,
                status=intent.status,
                purpose=intent.purpose,
                provider=intent.provider,
                created_at=intent.created_at,
                user_id=intent.user.id,  # Chỉ trả user_id
            )
            for intent in result["results"]
        ],
    )




@router.post("/callback/")
@router.get("/callback/")
@router.post("/webhook")
@router.get("/webhook")
def seapay_callback_fallback(request: HttpRequest):
    """Fallback callback endpoint for debugging"""
    print("=== SEPAY FALLBACK CALLBACK ===")
    print(f"Method: {request.method}")
    print(f"Path: {request.path}")
    
    return FallbackCallbackResponse(
        message="Fallback callback received",
        path=request.path,
        method=request.method
    )

