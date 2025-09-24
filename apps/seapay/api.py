import json
from ninja import Router
from ninja.errors import HttpError
from django.http import HttpRequest
from django.utils import timezone
from typing import Optional, List
from decimal import Decimal
from core.jwt_auth import JWTAuth

from apps.seapay.services.payment_service import PaymentService
from apps.seapay.services.wallet_topup_service import WalletTopupService
from apps.seapay.services.symbol_purchase_service import SymbolPurchaseService
from apps.seapay.models import OrderStatus, PaymentStatus
from apps.stock.models import Symbol
from apps.seapay.schemas import (
    CreatePaymentIntentRequest,
    CreatePaymentIntentResponse,
    PaymentIntentDetailResponse,
    WalletResponse,
    PaymentCallbackResponse,
    FallbackCallbackResponse,
    PaymentIntentOut,
    PaginatedPaymentIntent,
    UserResponse,
    CreateWalletTopupRequest,
    CreateWalletTopupResponse,
    WalletTopupStatusResponse,
    SepayWebhookRequest,
    SepayWebhookResponse,
    CreateSymbolOrderRequest,
    CreateSymbolOrderResponse,
    ProcessWalletPaymentResponse,
    CreateSepayPaymentResponse,
    SymbolAccessCheckResponse,
    UserSymbolLicenseResponse,
    PaginatedSymbolOrderHistory
)

router = Router()
payment_service = PaymentService()
topup_service = WalletTopupService()
symbol_purchase_service = SymbolPurchaseService()


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
    """SePay callback endpoint - handles both JSON and form data"""
    print("=== SEPAY CALLBACK RECEIVED ===")
    print(f"Method: {request.method}")
    print(f"Path: {request.path}")
    print(f"Headers: {dict(request.headers)}")
    print(f"Query params: {dict(request.GET)}")
    
    # Try multiple data parsing methods
    data = {}
    
    # Method 1: JSON body
    try:
        if request.body:
            data = json.loads(request.body)
            print("✅ Parsed JSON data:", data)
    except Exception as e:
        print(f"❌ JSON parsing error: {e}")
        
        # Method 2: Form data
        try:
            data = dict(request.POST)
            print("✅ Parsed form data:", data)
        except Exception as e2:
            print(f"❌ Form parsing error: {e2}")
            
            # Method 3: Query parameters
            try:
                data = dict(request.GET)
                print("✅ Using query params:", data)
            except Exception as e3:
                print(f"❌ Query param error: {e3}")
                return PaymentCallbackResponse(
                    message="Could not parse request data"
                )

    try:
        # Kiểm tra xem đây có phải là wallet topup không
        if data.get("content", "").startswith("TOPUP"):
            # Xử lý wallet topup callback
            result = topup_service.process_webhook_event({
                'id': data.get('id'),
                'gateway': data.get('gateway'),
                'transactionDate': data.get('transactionDate'),
                'accountNumber': data.get('accountNumber'),
                'subAccount': data.get('subAccount'),
                'code': data.get('code'),
                'content': data.get('content'),
                'transferType': data.get('transferType'),
                'description': data.get('description'),
                'transferAmount': data.get('transferAmount'),
                'referenceCode': data.get('referenceCode'),
                'accumulated': data.get('accumulated', 0)
            })
            print("✅ Wallet topup callback processed:", result)
        else:
            # Xử lý payment intent thông thường
            result = payment_service.process_callback(
                content=data.get("content", "").strip(),
                amount=Decimal(str(data.get("transferAmount", 0))),
                transfer_type=data.get("transferType", ""),
                reference_code=data.get("referenceCode", "")
            )
            print("✅ Payment callback processed:", result)
            
        return PaymentCallbackResponse(**result)
        
    except Exception as e:
        print(f"❌ Callback processing error: {e}")
        return PaymentCallbackResponse(
            message=f"Callback processing failed: {str(e)}"
        )


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

    valid_statuses = {choice for choice, _ in PaymentStatus.choices}
    resolved_status = status.strip() if isinstance(status, str) else None

    if not resolved_status:
        resolved_status = PaymentStatus.SUCCEEDED
    elif resolved_status not in valid_statuses:
        raise HttpError(400, "Invalid status")

    result = payment_service.get_paginated_payment_intents(
        user=user,
        page=page,
        limit=limit,
        search=search,
        status=resolved_status,
        purpose=purpose,
    )

    payment_intents: list[PaymentIntentOut] = []
    for intent in result["results"]:
        metadata = intent.metadata or {}
        payment_intents.append(
            PaymentIntentOut(
                id=str(intent.intent_id),
                order_code=intent.order_code,
                reference_code=metadata.get("reference_code"),
                amount=intent.amount,
                status=intent.status,
                purpose=intent.purpose,
                provider=metadata.get("provider", "sepay"),
                created_at=intent.created_at,
                user_id=intent.user_id,
            )
        )

    return PaginatedPaymentIntent(
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        user=UserResponse(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            is_active=user.is_active,
            date_joined=user.date_joined,
        ),
        results=payment_intents,
    )


@router.post("/wallet/topup/create", response=CreateWalletTopupResponse, auth=JWTAuth())
def create_wallet_topup(request: HttpRequest, data: CreateWalletTopupRequest):
    """
    Tạo yêu cầu nạp tiền vào ví
    
    Luồng:
    1. Tạo payment intent (purpose = wallet_topup)
    2. Tạo payment attempt với QR code
    3. Trả về thông tin QR để user thanh toán
    """
    try:
        if data.amount <= 0:
            raise HttpError(400, "Amount must be greater than 0")
        
        if data.amount > Decimal('100000000'): 
            raise HttpError(400, "Amount exceeds maximum limit")
        
        intent = topup_service.create_topup_intent(
            user=request.auth,
            amount=data.amount,
            currency=data.currency,
            expires_in_minutes=data.expires_in_minutes,
            metadata={
                'ip_address': request.META.get('REMOTE_ADDR'),
                'user_agent': request.META.get('HTTP_USER_AGENT'),
            }
        )
        
        attempt = topup_service.create_payment_attempt(
            intent=intent,
            bank_code=data.bank_code
        )
        
        return CreateWalletTopupResponse(
            intent_id=str(intent.intent_id),
            order_code=intent.order_code,
            amount=intent.amount,
            currency="VND",
            status=intent.status,
            qr_image_url=attempt.qr_image_url or "",
            account_number=attempt.account_number or "",
            account_name=attempt.account_name or "",
            transfer_content=attempt.transfer_content or "",
            bank_code=attempt.bank_code or "",
            expires_at=intent.expires_at.isoformat() if intent.expires_at else "",
            message="Topup request created successfully. Please scan QR code to complete payment."
        )
        
    except ValueError as e:
        raise HttpError(400, str(e))
    except Exception as e:
        raise HttpError(500, f"Failed to create topup request: {str(e)}")


@router.get("/wallet/topup/{intent_id}/status", response=WalletTopupStatusResponse, auth=JWTAuth())
def get_topup_status(request: HttpRequest, intent_id: str):
    """
    Kiểm tra trạng thái nạp tiền
    """
    try:
        status_data = topup_service.get_topup_status(intent_id, request.auth)
        
        intent = status_data['intent']
        attempt = status_data.get('attempt')
        payment = status_data.get('payment')
        ledger = status_data.get('ledger')
        
        return WalletTopupStatusResponse(
            intent_id=intent['id'],
            order_code=intent['order_code'],
            amount=Decimal(str(intent['amount'])),
            status=intent['status'],
            is_expired=intent['is_expired'],
            qr_image_url=attempt['qr_image_url'] if attempt else "",
            account_number=attempt['account_number'] if attempt else "",
            account_name=attempt['account_name'] if attempt else "",
            transfer_content=attempt['transfer_content'] if attempt else "",
            bank_code=attempt['bank_code'] if attempt else "",
            expires_at=intent['expires_at'] or "",
            payment_id=payment['id'] if payment else None,
            provider_payment_id=payment['provider_payment_id'] if payment else None,
            balance_before=ledger['balance_before'] if ledger else None,
            balance_after=ledger['balance_after'] if ledger else None,
            completed_at=payment['created_at'] if payment else None,
            message=f"Topup status: {intent['status']}"
        )
        
    except ValueError as e:
        raise HttpError(404, str(e))
    except Exception as e:
        raise HttpError(500, f"Failed to get topup status: {str(e)}")


@router.post("/symbol/order/create", response=CreateSymbolOrderResponse, auth=JWTAuth())
def create_symbol_order(request: HttpRequest, data: CreateSymbolOrderRequest):
    """
    Tạo đơn hàng mua quyền truy cập symbol
    
    Luồng:
    1. Validate items và tính tổng tiền
    2. Tạo PaySymbolOrder và PaySymbolOrderItem
    3. Trả về thông tin đơn hàng
    """
    try:
        user = request.auth
        
        if not data.items:
            raise HttpError(400, "Order must have at least one item")
        
        items = []
        for item in data.items:
            items.append({
                'symbol_id': item.symbol_id,
                'price': item.price,
                'license_days': item.license_days,
                'metadata': item.metadata or {}
            })
        
        order = symbol_purchase_service.create_symbol_order(
            user=user,
            items=items,
            payment_method=data.payment_method,
            description=data.description
        )
        
        symbol_ids = {item.symbol_id for item in order.items.all() if item.symbol_id}
        symbol_map = {symbol.id: symbol.name for symbol in Symbol.objects.filter(id__in=symbol_ids)} if symbol_ids else {}

        order_items = []
        for item in order.items.all():
            order_items.append({
                'symbol_id': item.symbol_id,
                'symbol_name': symbol_map.get(item.symbol_id),
                'price': item.price,
                'license_days': item.license_days,
                'metadata': item.metadata or {}
            })
        
        response_data = {
            'order_id': str(order.order_id),
            'total_amount': order.total_amount,
            'status': order.status,
            'payment_method': order.payment_method,
            'items': order_items,
            'created_at': order.created_at.isoformat(),
            'message': f"Order created successfully. Total: {order.total_amount} VND"
        }
        
        if order.payment_intent:
            response_data.update({
                'payment_intent_id': str(order.payment_intent.intent_id),
                'qr_code_url': order.payment_intent.qr_code_url,
                'deep_link': order.payment_intent.deep_link
            })
            
            # Update message for SePay orders
            if order.payment_method != 'wallet':
                response_data['message'] = f"Order created with SePay payment. Scan QR code to pay {order.total_amount} VND"
        
        return CreateSymbolOrderResponse(**response_data)
        
    except ValueError as e:
        # Handle insufficient balance exception with detailed info
        if isinstance(e.args[0], dict) and e.args[0].get('code') == 'INSUFFICIENT_BALANCE':
            error_info = e.args[0]
            # Return JSON response for insufficient balance
            from django.http import JsonResponse
            return JsonResponse({
                "error": "INSUFFICIENT_BALANCE", 
                "message": error_info['message'],
                "details": {
                    "required_amount": error_info['required_amount'],
                    "current_balance": error_info['current_balance'],
                    "insufficient_amount": error_info['insufficient_amount'],
                    "order_id": error_info['order_id'],
                    "topup_endpoint": error_info['topup_endpoint']
                }
            }, status=400)
        else:
            # Handle other ValueError exceptions
            raise HttpError(400, str(e))
    except Exception as e:
        raise HttpError(500, f"Failed to create order: {str(e)}")


@router.post("/symbol/order/{order_id}/pay-wallet", response=ProcessWalletPaymentResponse, auth=JWTAuth())
def pay_symbol_order_with_wallet(request: HttpRequest, order_id: str):
    """
    Thanh toán đơn hàng symbol bằng ví
    """
    try:
        user = request.auth
        
        result = symbol_purchase_service.process_wallet_payment(order_id, user)
        
        return ProcessWalletPaymentResponse(**result)
        
    except ValueError as e:
        raise HttpError(404, str(e))


@router.post("/symbol/order/{order_id}/pay-sepay", response=CreateSepayPaymentResponse, auth=JWTAuth())
def create_sepay_payment(request: HttpRequest, order_id: str):
    """
    Tạo payment intent cho thanh toán SePay cho đơn hàng symbol
    """
    try:
        user = request.auth
        
        result = symbol_purchase_service.create_sepay_payment_intent(order_id, user)
        
        return CreateSepayPaymentResponse(**result)
        
    except ValueError as e:
        raise HttpError(404, str(e))
    except Exception as e:
        raise HttpError(500, f"Failed to create payment intent: {str(e)}")


@router.post("/symbol/order/{order_id}/topup-sepay", response=CreateSepayPaymentResponse, auth=JWTAuth())
def create_sepay_topup_for_order(request: HttpRequest, order_id: str):
    """
    Tạo SePay QR để nạp tiền khi số dư không đủ thanh toán đơn hàng
    """
    try:
        user = request.auth
        
        result = symbol_purchase_service.create_sepay_topup_for_insufficient_order(order_id, user)
        
        return CreateSepayPaymentResponse(**result)
        
    except ValueError as e:
        raise HttpError(400, str(e))
    except Exception as e:
        raise HttpError(500, f"Failed to create topup intent: {str(e)}")


@router.get("/symbol/{symbol_id}/access", response=SymbolAccessCheckResponse, auth=JWTAuth())
def check_symbol_access(request: HttpRequest, symbol_id: int):
    """
    Kiểm tra user có quyền truy cập symbol không
    
    Returns:
        Thông tin license và quyền truy cập
    """
    try:
        user = request.auth
        
        result = symbol_purchase_service.check_symbol_access(user, symbol_id)
        
        return SymbolAccessCheckResponse(**result)
        
    except Exception as e:
        raise HttpError(500, f"Failed to check access: {str(e)}")


@router.get("/symbol/licenses", response=List[UserSymbolLicenseResponse], auth=JWTAuth())
def get_user_symbol_licenses(request: HttpRequest, page: int = 1, limit: int = 20):
    """
    Lấy tất cả licenses của user
    
    Returns:
        List các symbol license
    """
    try:
        user = request.auth
        
        licenses_data = symbol_purchase_service.get_user_symbol_licenses(user, page, limit)
        
        return [UserSymbolLicenseResponse(**license) for license in licenses_data['results']]
        
    except Exception as e:
        raise HttpError(500, f"Failed to get licenses: {str(e)}")


@router.get("/symbol/orders/history", response=PaginatedSymbolOrderHistory, auth=JWTAuth())
def get_order_history(
    request: HttpRequest,
    page: int = 1,
    limit: int = 20,
    status: str | None = None,
):
    """
    Lấy lịch sử mua symbol của user
    
    Returns:
        Paginated order history
    """
    try:
        user = request.auth
        
        # Validate pagination
        if limit > 100:
            limit = 100
        if limit <= 0:
            limit = 20
        if page <= 0:
            page = 1

        if status and status not in {choice for choice, _ in OrderStatus.choices}:
            raise HttpError(400, "Invalid status")

        orders_data = symbol_purchase_service.get_order_history(
            user=user,
            page=page,
            limit=limit,
            status=status,
        )

        return PaginatedSymbolOrderHistory(**orders_data)
        
    except Exception as e:
        raise HttpError(500, f"Failed to get order history: {str(e)}")

