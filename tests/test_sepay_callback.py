#!/usr/bin/env python
"""
🧪 Test SePay Callback Processing

CÁCH SỬ DỤNG:
1. Chạy trực tiếp file này: python tests/test_sepay_callback.py
2. Hoặc import và gọi từng function để test riêng biệt

MỤC ĐÍCH:
- Test xử lý webhook callback thực từ SePay
- Kiểm tra logic sync payment intent và order status
- Debug callback processing với data thật

REQUIREMENTS:
- Django server phải đang chạy hoặc có database connection
- Có data payment intent trong database để test
"""

import os
import django
import json
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.seapay.services.payment_service import PaymentService

def test_real_sepay_callback():
    """
    🚀 Test callback với data thực từ SePay
    
    CÁCH CHẠY:
        python tests/test_sepay_callback.py
    
    HOẶC:
        python -c "from tests.test_sepay_callback import test_real_sepay_callback; test_real_sepay_callback()"
    
    KẾT QUẢ MONG ĐỢI:
        ✅ Payment intent được tìm thấy và cập nhật status
        ✅ Order status được sync từ pending_payment → paid
        ✅ License được tạo cho user
    """
    
    print("🧪 TESTING REAL SEPAY CALLBACK DATA")
    print("=" * 60)
    
    # Data thực từ SePay webhook - thay đổi content để test với data của bạn
    real_webhook_data = {
        'gateway': 'BIDV',
        'transactionDate': '2025-09-23 09:45:00',
        'accountNumber': '1160976779',
        'subAccount': '96247CISI1',
        'code': None,
        'content': 'PAY73B54FC61758595354',  # 🔄 Thay đổi content này để test với data thật
        'transferType': 'in',
        'description': 'BankAPINotify PAY73B54FC61758595354',
        'transferAmount': 10000,  # 🔄 Thay đổi amount để match với payment intent
        'referenceCode': 'ff3bafde-f4e9-4296-9695-0c7b17bf8ccb',
        'accumulated': 0,
        'id': 24175231
    }
    
    print("📨 Real Webhook Data:")
    print(json.dumps(real_webhook_data, indent=2, default=str))
    print()
    
    # Test với payment service
    try:
        payment_service = PaymentService()
        
        print("🚀 Processing callback with PaymentService...")
        result = payment_service.process_callback(
            content=real_webhook_data.get("content", "").strip(),
            amount=Decimal(str(real_webhook_data.get("transferAmount", 0))),
            transfer_type=real_webhook_data.get("transferType", ""),
            reference_code=real_webhook_data.get("referenceCode", "")
        )
        
        print("✅ Payment Service Result:")
        print(json.dumps(result, indent=2, default=str))
        
    except Exception as e:
        print(f"❌ Payment Service Error: {e}")
        import traceback
        print("📋 Full traceback:")
        traceback.print_exc()
    
    print()
    print("=" * 60)

def check_payment_intent_in_db():
    """
    🔍 Kiểm tra payment intents trong database
    
    CÁCH CHẠY:
        python -c "from tests.test_sepay_callback import check_payment_intent_in_db; check_payment_intent_in_db()"
    
    MỤC ĐÍCH:
        - Xem tất cả payment intents gần đây
        - Tìm payment intent cụ thể theo order_code
        - Debug status của payments
    """
    
    print("🔍 CHECKING PAYMENT INTENTS IN DATABASE")
    print("=" * 60)
    
    from apps.seapay.models import PayPaymentIntent
    
    try:
        # Lấy payment intents gần đây
        intents = PayPaymentIntent.objects.all().order_by('-created_at')[:10]
        
        print(f"📊 Found {intents.count()} recent payment intents:")
        for intent in intents:
            print(f"  🔹 ID: {intent.intent_id}")
            print(f"     Purpose: {intent.purpose}")
            print(f"     Amount: {intent.amount}")
            print(f"     Status: {intent.status}")
            print(f"     Order Code: {intent.order_code}")
            print(f"     Created: {intent.created_at}")
            print()
            
        # 🔍 TÌM INTENT CỤ THỂ - thay đổi content này để tìm payment intent của bạn
        search_content = 'PAY73B54FC61758595354'  # 🔄 Thay đổi đây
        matching_intents = PayPaymentIntent.objects.filter(
            order_code__icontains=search_content
        )
        
        print(f"🎯 Matching intents for {search_content}: {matching_intents.count()}")
        for intent in matching_intents:
            print(f"  ✅ Found: {intent.intent_id} - {intent.status}")
            
    except Exception as e:
        print(f"❌ Database error: {e}")
    
    print("=" * 60)

def test_wallet_topup_callback():
    """
    💰 Test wallet topup callback
    
    CÁCH CHẠY:
        python -c "from tests.test_sepay_callback import test_wallet_topup_callback; test_wallet_topup_callback()"
    
    MỤC ĐÍCH:
        - Test xử lý webhook cho wallet topup
        - Kiểm tra logic cập nhật số dư ví
    """
    
    print("💰 TESTING WALLET TOPUP CALLBACK")
    print("=" * 60)
    
    # Data mẫu cho wallet topup
    topup_webhook_data = {
        'gateway': 'BIDV',
        'transactionDate': '2025-09-23 10:00:00',
        'accountNumber': '1160976779',
        'subAccount': '96247CISI1',
        'code': 'FT25001123456789',
        'content': 'TOPUP_ABC123_456789',  # 🔄 Thay đổi content này
        'transferType': 'in',
        'description': 'Chuyen tien nap vi',
        'transferAmount': 100000,  # 🔄 Thay đổi amount
        'referenceCode': 'topup-ref-123',
        'accumulated': 1000000,
        'id': 24175232
    }
    
    print("📨 Wallet Topup Data:")
    print(json.dumps(topup_webhook_data, indent=2, default=str))
    print()
    
    try:
        from apps.seapay.services.wallet_topup_service import WalletTopupService
        
        topup_service = WalletTopupService()
        
        print("🚀 Processing wallet topup...")
        result = topup_service.process_webhook_event(topup_webhook_data)
        
        print("✅ Wallet Topup Result:")
        print(json.dumps(result, indent=2, default=str))
        
    except Exception as e:
        print(f"❌ Wallet Topup Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("=" * 60)

def test_order_status_sync():
    """
    🛒 Test order status synchronization
    
    CÁCH CHẠY:
        python -c "from tests.test_sepay_callback import test_order_status_sync; test_order_status_sync()"
    
    MỤC ĐÍCH:
        - Kiểm tra orders có status pending_payment
        - Test logic sync order status sau khi payment thành công
    """
    
    print("🛒 TESTING ORDER STATUS SYNC")
    print("=" * 60)
    
    from apps.seapay.models import PaySymbolOrder, PayPaymentIntent
    
    try:
        # Kiểm tra pending orders
        pending_orders = PaySymbolOrder.objects.filter(status='pending_payment')
        
        print(f"📊 Found {pending_orders.count()} pending orders:")
        for order in pending_orders[:5]:  # Show first 5
            print(f"  🔹 Order ID: {order.order_id}")
            print(f"     Total: {order.total_amount}")
            print(f"     Payment Method: {order.payment_method}")
            print(f"     Payment Intent: {order.payment_intent.intent_id if order.payment_intent else 'None'}")
            print(f"     Created: {order.created_at}")
            print()
        
        # Kiểm tra succeeded payment intents
        succeeded_intents = PayPaymentIntent.objects.filter(status='succeeded')
        
        print(f"💚 Found {succeeded_intents.count()} succeeded payment intents:")
        for intent in succeeded_intents[:5]:  # Show first 5
            print(f"  ✅ Intent ID: {intent.intent_id}")
            print(f"     Order Code: {intent.order_code}")
            print(f"     Amount: {intent.amount}")
            
            # Tìm order tương ứng
            related_orders = PaySymbolOrder.objects.filter(payment_intent=intent)
            print(f"     Related Orders: {related_orders.count()}")
            for order in related_orders:
                print(f"       🛒 Order {order.order_id} - Status: {order.status}")
            print()
            
    except Exception as e:
        print(f"❌ Database error: {e}")
    
    print("=" * 60)

if __name__ == "__main__":
    print("🧪 SEPAY CALLBACK TESTING SUITE")
    print("=" * 80)
    print()
    print("📋 Available Tests:")
    print("  1️⃣  check_payment_intent_in_db() - Xem payment intents trong DB")
    print("  2️⃣  test_real_sepay_callback() - Test callback với data thật")  
    print("  3️⃣  test_wallet_topup_callback() - Test wallet topup")
    print("  4️⃣  test_order_status_sync() - Test order status sync")
    print()
    print("🚀 Running all tests...")
    print()
    
    # Chạy tất cả tests
    check_payment_intent_in_db()
    print()
    test_real_sepay_callback()
    print()
    test_wallet_topup_callback()
    print()
    test_order_status_sync()
    
    print()
    print("✅ All tests completed!")
    print("=" * 80)