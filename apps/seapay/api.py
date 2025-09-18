from ninja import Router, Schema
from ninja.errors import HttpError
from django.http import HttpRequest
from apps.seapay.models import SeapayOrder
from django.db import transaction
from decimal import Decimal
from apps.seapay.utils.signature import verify_signature
router = Router()
import json
class CreateOrderIn(Schema):
    order_id: str
    amount: Decimal
    description: str = ""

class CreateOrderOut(Schema):
    order_id: str
    qr_code_url: str
    transfer_content: str
    status: str

@router.post("/create", response=CreateOrderOut)
def create_order(request, data: CreateOrderIn):
    # 1. Lưu đơn hàng vào DB trạng thái pending
    with transaction.atomic():
        order, created = SeapayOrder.objects.get_or_create(
            order_id=data.order_id,
            defaults={
                "amount": data.amount,
                "description": data.description,
                "status": "pending",
            },
        )
        if not created:
            raise HttpError(400, f"Order {data.order_id} already exists")

        # 2. Sinh nội dung chuyển khoản (nội dung định danh cho đơn hàng)
        transfer_content = f"SEAPAY_{data.order_id}"

        # 3. Sinh link QR động theo chuẩn sepay.vn
        qr_code_url = (
            f"https://qr.sepay.vn/img?acc=96247CISI1"
            f"&bank=BIDV"
            f"&amount={int(data.amount)}"
            f"&des={transfer_content}"
            f"&template=compact"
        )
        # https://qr.sepay.vn/img?acc=96247CISI1&bank=BIDV&amount=2000&des=gdsgd&template=compact
        # account_name='TO TRONG HIEU'
        # qr_code_url = (
        #     f"https://img.vietqr.io/image/{970418}-{1160976779}-compact.png"
        #     f"?amount={int(data.amount)}&addInfo={transfer_content}&accountName={account_name}"
        # )
        order.qr_code_url = qr_code_url
        order.save()

    return CreateOrderOut(
        order_id=order.order_id,
        qr_code_url=order.qr_code_url,
        transfer_content=transfer_content,
        status=order.status
    )

@router.post("/callback")
def seapay_callback(request: HttpRequest):
   
    try:
        data = data = json.loads(request.body)
        print("Callback data:", data)
    except Exception:
        raise HttpError(400, "Invalid JSON")

    order_id = data.get("order_id")
    status = data.get("status")
    amount = data.get("amount")

    try:
        order = SeapayOrder.objects.get(order_id=order_id)
    except SeapayOrder.DoesNotExist:
        raise HttpError(404, "Order not found")

    if Decimal(amount) != order.amount:
        raise HttpError(400, "Amount mismatch")

    with transaction.atomic():
        if status == "success":
            order.status = "paid"
        else:
            order.status = "failed"
        order.save(update_fields=["status", "updated_at"])

    return {"message": "OK", "order_id": order_id, "status": order.status}

