#!/usr/bin/env python
"""
🛒 Test Symbol Order Payment Processing

CÁCH SỬ DỤNG:
1. Chạy trực tiếp: python tests/test_order_payment.py
2. Hoặc import function cụ thể để test

MỤC ĐÍCH:
- Test callback processing cho thanh toán đơn hàng symbol
- Kiểm tra sync giữa PaymentIntent và SymbolOrder status
- Debug order payment logic với data thật

REQUIREMENTS:
- Có pending orders trong database
- Payment intents đã được tạo
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.seapay.services.payment_service import PaymentService
from decimal import Decimal

def test_order_payment_callback():
    """
    🚀 Test callback với order payment real data
    
    CÁCH CHẠY:
        python tests/test_order_payment.py
    
    HOẶC:
        python -c "from tests.test_order_payment import test_order_payment_callback; test_order_payment_callback()"
    
    KẾT QUẢ MONG ĐỢI:
        ✅ Payment intent status: pending → succeeded
        ✅ Symbol order status: pending_payment → paid
        ✅ User license được tạo
    """
    
    print("🧪 TEST ORDER PAYMENT CALLBACK")
    print("=" * 60)
    
    # 🔄 Real callback data từ logs - THAY ĐỔI DATA NÀY THEO LOG THỰC TẾ
    callback_data = {
        'content': 'PAYBF34B5431758596460',  # 🔄 Thay content từ SePay logs
        'transferAmount': 10000,  # 🔄 Thay amount theo thanh toán thực tế
        'transferType': 'in',
        'referenceCode': 'dd9c90c1-6b4a-4aa0-a386-42d6ed6d608d'  # 🔄 Thay reference
    }
    
    print(f"📨 Callback data: {callback_data}")
    print()
    
    try:
        service = PaymentService()
        result = service.process_callback(
            content=callback_data['content'],
            amount=Decimal(str(callback_data['transferAmount'])),
            transfer_type=callback_data['transferType'],
            reference_code=callback_data['referenceCode']
        )
        
        print("✅ Callback result:")
        import json
        print(json.dumps(result, indent=2, default=str))
        
    except Exception as e:
        print(f"❌ Callback error: {e}")
        import traceback
        print("📋 Traceback:")
        traceback.print_exc()
    
    print("=" * 60)

def check_symbol_order_status():
    """
    📊 Kiểm tra trạng thái symbol orders
    
    CÁCH CHẠY:
        python -c "from tests.test_order_payment import check_symbol_order_status; check_symbol_order_status()"
    
    MỤC ĐÍCH:
        - Xem tất cả orders gần đây và status
        - Kiểm tra relationship giữa Order và PaymentIntent
        - Debug order payment sync issues
    """
    
    print("📊 SYMBOL ORDER STATUS CHECK")
    print("=" * 60)
    
    from apps.seapay.models import PaySymbolOrder, PayPaymentIntent
    
    # Kiểm tra orders gần đây
    orders = PaySymbolOrder.objects.all().order_by('-created_at')[:10]
    
    print(f"📋 Recent Symbol Orders ({orders.count()}):")
    for order in orders:
        print(f"  🔹 Order ID: {order.order_id}")
        print(f"     Status: {order.status}")
        print(f"     Amount: {order.total_amount}")
        print(f"     Payment Method: {order.payment_method}")
        print(f"     Payment Intent: {order.payment_intent_id}")
        print(f"     Created: {order.created_at}")
        
        # Check payment intent status
        if order.payment_intent_id:
            try:
                intent = PayPaymentIntent.objects.get(intent_id=order.payment_intent_id)
                print(f"     ✅ Intent Status: {intent.status}")
                print(f"     ✅ Intent Order Code: {intent.order_code}")
            except PayPaymentIntent.DoesNotExist:
                print(f"     ❌ Intent Status: NOT FOUND")
        print()
    
    print("=" * 60)

def check_pending_orders():
    """
    ⏳ Kiểm tra orders đang pending
    
    CÁCH CHẠY:
        python -c "from tests.test_order_payment import check_pending_orders; check_pending_orders()"
    
    MỤC ĐÍCH:
        - Tìm orders có status pending_payment
        - Kiểm tra payment intents tương ứng
        - Identify orders cần được sync
    """
    
    print("⏳ PENDING ORDERS CHECK")
    print("=" * 60)
    
    from apps.seapay.models import PaySymbolOrder, PayPaymentIntent
    
    # Tìm pending orders
    pending_orders = PaySymbolOrder.objects.filter(status='pending_payment')
    
    print(f"📊 Found {pending_orders.count()} pending orders:")
    
    for order in pending_orders:
        print(f"  ⏳ Order ID: {order.order_id}")
        print(f"     Amount: {order.total_amount}")
        print(f"     Payment Method: {order.payment_method}")
        print(f"     Created: {order.created_at}")
        
        if order.payment_intent_id:
            try:
                intent = PayPaymentIntent.objects.get(intent_id=order.payment_intent_id)
                print(f"     💳 Payment Intent: {intent.intent_id}")
                print(f"     💳 Intent Status: {intent.status}")
                print(f"     💳 Order Code: {intent.order_code}")
                
                # Check if intent is succeeded but order still pending
                if intent.status == 'succeeded' and order.status == 'pending_payment':
                    print(f"     ⚠️  SYNC ISSUE: Intent succeeded but order still pending!")
                    
            except PayPaymentIntent.DoesNotExist:
                print(f"     ❌ Payment Intent NOT FOUND")
        else:
            print(f"     ❌ No Payment Intent linked")
        print()
    
    print("=" * 60)

def test_specific_order_callback(order_code, amount):
    """
    🎯 Test callback cho order cụ thể
    
    CÁCH CHẠY:
        python -c "from tests.test_order_payment import test_specific_order_callback; test_specific_order_callback('PAY123456789', 50000)"
    
    PARAMETERS:
        order_code (str): Mã order code từ SePay (VD: PAY123456789)
        amount (int): Số tiền thanh toán
    """
    
    print(f"🎯 TEST SPECIFIC ORDER CALLBACK: {order_code}")
    print("=" * 60)
    
    try:
        service = PaymentService()
        result = service.process_callback(
            content=order_code,
            amount=Decimal(str(amount)),
            transfer_type='in',
            reference_code=f'test-ref-{order_code}'
        )
        
        print("✅ Callback result:")
        import json
        print(json.dumps(result, indent=2, default=str))
        
        # Check order status after callback
        from apps.seapay.models import PaySymbolOrder, PayPaymentIntent
        
        intent = PayPaymentIntent.objects.filter(order_code=order_code).first()
        if intent:
            print(f"\n📋 After callback:")
            print(f"   Intent Status: {intent.status}")
            
            orders = PaySymbolOrder.objects.filter(payment_intent_id=intent.intent_id)
            for order in orders:
                print(f"   Order {order.order_id} Status: {order.status}")
        
    except Exception as e:
        print(f"❌ Callback error: {e}")
        import traceback
        traceback.print_exc()
    
    print("=" * 60)

if __name__ == "__main__":
    print("🛒 SYMBOL ORDER PAYMENT TESTING SUITE")
    print("=" * 80)
    print()
    print("📋 Available Tests:")
    print("  1️⃣  check_symbol_order_status() - Xem tất cả orders và status")
    print("  2️⃣  check_pending_orders() - Tìm orders đang pending")
    print("  3️⃣  test_order_payment_callback() - Test callback với data mẫu")
    print("  4️⃣  test_specific_order_callback(order_code, amount) - Test order cụ thể")
    print()
    print("💡 Tips:")
    print("   - Sửa callback_data trong test_order_payment_callback() với data thật")
    print("   - Dùng test_specific_order_callback() để test order cụ thể")
    print("   - Check pending_orders trước khi test callback")
    print()
    print("🚀 Running basic checks...")
    print()
    
    # Chạy basic tests
    check_symbol_order_status()
    print()
    check_pending_orders()
    print()
    test_order_payment_callback()
    
    print()
    print("✅ Basic tests completed!")
    print("=" * 80)