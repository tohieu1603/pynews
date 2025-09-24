#!/usr/bin/env python
"""
🔄 Test Callback Sync Logic

CÁCH SỬ DỤNG:
1. Chạy trực tiếp: python tests/test_callback_sync.py
2. Hoặc import các function để test riêng biệt

MỤC ĐÍCH:
- Test logic sync order status sau khi callback
- Verify payment intent → order status sync
- Test edge cases: duplicate callbacks, already processed
- Debug callback processing issues

REQUIREMENTS:
- Django environment setup
- Payment intents và orders trong database
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

def test_callback_with_sync():
    """
    🔄 Test callback với logic sync order status mới
    
    CÁCH CHẠY:
        python tests/test_callback_sync.py
    
    HOẶC:
        python -c "from tests.test_callback_sync import test_callback_with_sync; test_callback_with_sync()"
    
    MỤC ĐÍCH:
        - Test callback processing với data đã có trong DB
        - Verify order status sync logic
        - Check duplicate callback handling
    """
    
    print("🧪 TEST CALLBACK WITH ORDER SYNC")
    print("=" * 60)
    
    from apps.seapay.services.payment_service import PaymentService
    from decimal import Decimal
    import json
    
    # 🔄 Test cases - thay đổi content theo data thực tế trong DB
    test_cases = [
        {
            'name': 'Already succeeded intent',
            'content': 'PAY73B54FC61758595354',  # 🔄 Thay content đã có trong DB
            'amount': 10000,  # 🔄 Thay amount matching với payment intent
            'transferType': 'in',
            'referenceCode': 'test-ref-123'
        },
        {
            'name': 'Recent callback data',
            'content': 'PAYBF34B5431758596460',  # 🔄 Thay content từ logs gần đây
            'amount': 10000,  # 🔄 Thay amount matching
            'transferType': 'in', 
            'referenceCode': 'dd9c90c1-6b4a-4aa0-a386-42d6ed6d608d'
        },
        {
            'name': 'Wallet topup test',
            'content': 'TOPUP_ABC123_456789',  # 🔄 Test wallet topup callback
            'amount': 50000,
            'transferType': 'in',
            'referenceCode': 'topup-ref-123'
        }
    ]
    
    service = PaymentService()
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"📋 Test Case {i}: {test_case['name']}")
        print(f"   Content: {test_case['content']}")
        print(f"   Amount: {test_case['amount']} VND")
        print()
        
        try:
            result = service.process_callback(
                content=test_case['content'],
                amount=Decimal(str(test_case['amount'])),
                transfer_type=test_case['transferType'],
                reference_code=test_case['referenceCode']
            )
            
            print("✅ Callback Result:")
            print(json.dumps(result, indent=2, default=str, ensure_ascii=False))
            
            # Check specific results
            if result.get('status') == 'success':
                print(f"🎉 Callback processed successfully!")
                if result.get('order_id'):
                    print(f"📦 Order synced: {result['order_id']}")
                if result.get('payment_intent_id'):
                    print(f"💳 Payment intent: {result['payment_intent_id']}")
            else:
                print(f"⚠️  Callback status: {result.get('status')}")
                print(f"📝 Message: {result.get('message')}")
            
        except Exception as e:
            print(f"❌ Callback processing error: {e}")
            import traceback
            print("📋 Traceback:")
            traceback.print_exc()
        
        print()
        print("-" * 40)
        print()

def check_payment_intent_order_sync():
    """
    📊 Kiểm tra sync giữa payment intents và orders
    
    CÁCH CHẠY:
        python -c "from tests.test_callback_sync import check_payment_intent_order_sync; check_payment_intent_order_sync()"
    
    MỤC ĐÍCH:
        - Tìm payment intents đã succeeded
        - Kiểm tra orders tương ứng có được sync không
        - Identify sync issues
    """
    
    print("📊 CHECKING PAYMENT INTENT ↔ ORDER SYNC")
    print("=" * 60)
    
    from apps.seapay.models import PayPaymentIntent, PaySymbolOrder
    
    # Tìm succeeded payment intents
    succeeded_intents = PayPaymentIntent.objects.filter(status='succeeded').order_by('-updated_at')[:10]
    
    print(f"💚 Found {succeeded_intents.count()} succeeded payment intents:")
    
    sync_issues = []
    
    for intent in succeeded_intents:
        print(f"\n🔹 Intent: {intent.intent_id}")
        print(f"   Order Code: {intent.order_code}")
        print(f"   Amount: {intent.amount} VND")
        print(f"   Purpose: {intent.purpose}")
        print(f"   Updated: {intent.updated_at}")
        
        # Tìm orders liên quan
        related_orders = PaySymbolOrder.objects.filter(payment_intent_id=intent.intent_id)
        
        if related_orders.exists():
            print(f"   📦 Related Orders ({related_orders.count()}):")
            for order in related_orders:
                print(f"      🛒 {order.order_id} - Status: {order.status}")
                
                # Check sync issue
                if intent.status == 'succeeded' and order.status != 'paid':
                    sync_issues.append({
                        'intent_id': intent.intent_id,
                        'order_id': order.order_id,
                        'intent_status': intent.status,
                        'order_status': order.status
                    })
                    print(f"      ⚠️  SYNC ISSUE: Intent succeeded but order status is {order.status}")
        else:
            print(f"   ❌ No related orders found")
    
    # Summary of sync issues
    if sync_issues:
        print(f"\n⚠️  FOUND {len(sync_issues)} SYNC ISSUES:")
        for issue in sync_issues:
            print(f"   🔸 Intent {issue['intent_id']} → Order {issue['order_id']}")
            print(f"      Intent: {issue['intent_status']} vs Order: {issue['order_status']}")
    else:
        print(f"\n✅ All payment intents and orders are in sync!")
    
    print("=" * 60)

def test_duplicate_callback_handling():
    """
    🔁 Test xử lý duplicate callbacks
    
    CÁCH CHẠY:
        python -c "from tests.test_callback_sync import test_duplicate_callback_handling; test_duplicate_callback_handling()"
    
    MỤC ĐÍCH:
        - Test callback với same content multiple times
        - Verify idempotent behavior
        - Check không tạo duplicate records
    """
    
    print("🔁 TEST DUPLICATE CALLBACK HANDLING")
    print("=" * 60)
    
    from apps.seapay.services.payment_service import PaymentService
    from decimal import Decimal
    import json
    
    # 🔄 Sử dụng content đã có trong DB để test duplicate
    test_content = 'PAY73B54FC61758595354'  # 🔄 Thay content thực tế
    test_amount = 10000  # 🔄 Thay amount thực tế
    
    service = PaymentService()
    
    print(f"📋 Testing duplicate callbacks for: {test_content}")
    print()
    
    # Gửi callback lần 1
    print("1️⃣  First callback:")
    try:
        result1 = service.process_callback(
            content=test_content,
            amount=Decimal(str(test_amount)),
            transfer_type='in',
            reference_code='duplicate-test-1'
        )
        print("✅ First callback result:")
        print(json.dumps(result1, indent=2, default=str, ensure_ascii=False))
    except Exception as e:
        print(f"❌ First callback error: {e}")
        result1 = None
    
    print()
    
    # Gửi callback lần 2 (duplicate)
    print("2️⃣  Second callback (duplicate):")
    try:
        result2 = service.process_callback(
            content=test_content,
            amount=Decimal(str(test_amount)),
            transfer_type='in',
            reference_code='duplicate-test-2'
        )
        print("✅ Second callback result:")
        print(json.dumps(result2, indent=2, default=str, ensure_ascii=False))
    except Exception as e:
        print(f"❌ Second callback error: {e}")
        result2 = None
    
    # So sánh kết quả
    if result1 and result2:
        print("\n🔍 Comparing results:")
        if result1.get('payment_intent_id') == result2.get('payment_intent_id'):
            print("✅ Same payment intent processed (good)")
        else:
            print("⚠️  Different payment intents (potential issue)")
            
        if result1.get('status') == result2.get('status'):
            print("✅ Same status returned (good)")
        else:
            print("⚠️  Different status (potential issue)")
    
    print("=" * 60)

def test_wallet_topup_callback():
    """
    💰 Test wallet topup callback specifically
    
    CÁCH CHẠY:
        python -c "from tests.test_callback_sync import test_wallet_topup_callback; test_wallet_topup_callback()"
    
    MỤC ĐÍCH:
        - Test callback cho wallet topup (content bắt đầu với TOPUP)
        - Verify wallet balance update
        - Check topup service integration
    """
    
    print("💰 TEST WALLET TOPUP CALLBACK")
    print("=" * 60)
    
    from apps.seapay.services.wallet_topup_service import WalletTopupService
    import json
    
    # 🔄 Mock wallet topup callback data
    topup_callback_data = {
        'id': 'test_topup_123',
        'gateway': 'BIDV',
        'transactionDate': '2025-09-23 10:00:00',
        'accountNumber': '1160976779',
        'subAccount': '96247CISI1',
        'code': 'FT25001123456789',
        'content': 'TOPUP_TEST123_456789',  # 🔄 Thay content theo topup intent thực tế
        'transferType': 'in',
        'description': 'Chuyen tien nap vi test',
        'transferAmount': 25000,  # 🔄 Thay amount
        'referenceCode': 'topup-test-ref-123',
        'accumulated': 1000000
    }
    
    print("📨 Topup Callback Data:")
    print(json.dumps(topup_callback_data, indent=2, ensure_ascii=False))
    print()
    
    try:
        service = WalletTopupService()
        
        print("🚀 Processing wallet topup callback...")
        result = service.process_webhook_event(topup_callback_data)
        
        print("✅ Topup Callback Result:")
        print(json.dumps(result, indent=2, default=str, ensure_ascii=False))
        
        if result.get('status') == 'success':
            print("🎉 Wallet topup processed successfully!")
            if result.get('payment_id'):
                print(f"💳 Payment created: {result['payment_id']}")
            if result.get('balance_updated'):
                print(f"💰 Wallet balance updated")
        
    except Exception as e:
        print(f"❌ Topup callback error: {e}")
        import traceback
        traceback.print_exc()
    
    print("=" * 60)

def debug_specific_callback(content, amount):
    """
    🐛 Debug callback cụ thể
    
    CÁCH CHẠY:
        python -c "from tests.test_callback_sync import debug_specific_callback; debug_specific_callback('PAY123456789', 50000)"
    
    PARAMETERS:
        content (str): Order code hoặc content từ SePay
        amount (int): Số tiền
    """
    
    print(f"🐛 DEBUGGING CALLBACK: {content}")
    print("=" * 60)
    
    from apps.seapay.models import PayPaymentIntent, PaySymbolOrder
    from apps.seapay.services.payment_service import PaymentService
    from decimal import Decimal
    import json
    
    # 1. Kiểm tra payment intent có tồn tại không
    print("1️⃣  Checking payment intent in database...")
    intent = PayPaymentIntent.objects.filter(order_code=content).first()
    
    if intent:
        print(f"✅ Found payment intent: {intent.intent_id}")
        print(f"   Status: {intent.status}")
        print(f"   Amount: {intent.amount}")
        print(f"   Purpose: {intent.purpose}")
        
        # Check related orders
        orders = PaySymbolOrder.objects.filter(payment_intent_id=intent.intent_id)
        print(f"   Related orders: {orders.count()}")
        for order in orders:
            print(f"      🛒 {order.order_id} - {order.status}")
    else:
        print(f"❌ No payment intent found for: {content}")
    
    print()
    
    # 2. Process callback
    print("2️⃣  Processing callback...")
    try:
        service = PaymentService()
        result = service.process_callback(
            content=content,
            amount=Decimal(str(amount)),
            transfer_type='in',
            reference_code=f'debug-{content}'
        )
        
        print("✅ Callback Result:")
        print(json.dumps(result, indent=2, default=str, ensure_ascii=False))
        
    except Exception as e:
        print(f"❌ Callback error: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    
    # 3. Check state after callback
    print("3️⃣  Checking state after callback...")
    intent_after = PayPaymentIntent.objects.filter(order_code=content).first()
    if intent_after:
        print(f"✅ Payment intent status: {intent_after.status}")
        
        orders_after = PaySymbolOrder.objects.filter(payment_intent_id=intent_after.intent_id)
        for order in orders_after:
            print(f"🛒 Order {order.order_id} status: {order.status}")
    
    print("=" * 60)

if __name__ == "__main__":
    print("🔄 CALLBACK SYNC TESTING SUITE")
    print("=" * 80)
    print()
    print("📋 Available Tests:")
    print("  1️⃣  test_callback_with_sync() - Test callback với sync logic")
    print("  2️⃣  check_payment_intent_order_sync() - Kiểm tra sync issues")
    print("  3️⃣  test_duplicate_callback_handling() - Test duplicate callbacks")
    print("  4️⃣  test_wallet_topup_callback() - Test wallet topup callback")
    print("  5️⃣  debug_specific_callback(content, amount) - Debug callback cụ thể")
    print()
    print("💡 Tips:")
    print("   - Sửa test_cases với content thực tế trong database")
    print("   - Check payment intents và orders trước khi test")
    print("   - Use debug_specific_callback để test content cụ thể")
    print()
    print("🚀 Running basic tests...")
    print()
    
    # Run basic tests
    check_payment_intent_order_sync()
    print()
    test_callback_with_sync()
    print()
    test_duplicate_callback_handling()
    
    print()
    print("✅ Basic tests completed!")
    print("💡 Tip: Use debug_specific_callback('YOUR_CONTENT', AMOUNT) for specific debugging")
    print("=" * 80)