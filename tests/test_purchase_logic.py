#!/usr/bin/env python3
"""
🛒 Test Symbol Purchase Logic

CÁCH SỬ DỤNG:
1. Cập nhật JWT_TOKEN với token hợp lệ
2. Chạy: python tests/test_purchase_logic.py
3. Hoặc test từng function riêng biệt

MỤC ĐÍCH:
- Test logic mua symbol với wallet (đủ/không đủ tiền)
- Test logic mua symbol với SePay  
- Test tự động tạo QR code cho SePay payments
- Verify order status transitions

REQUIREMENTS:
- Server đang chạy tại localhost:8000
- User có JWT token hợp lệ
- Database có symbol data
"""

import requests
import json
import time

# 🔄 CẬP NHẬT CONFIG NÀY
BASE_URL = "http://localhost:8000"
JWT_TOKEN = "YOUR_JWT_TOKEN_HERE"  # 🔄 Thay đổi JWT token ở đây

headers = {
    "Authorization": f"Bearer {JWT_TOKEN}",
    "Content-Type": "application/json"
}

def check_wallet_balance():
    """
    💰 Kiểm tra số dư ví hiện tại
    
    CÁCH CHẠY:
        python -c "from tests.test_purchase_logic import check_wallet_balance; check_wallet_balance()"
    """
    
    print("💰 CHECKING WALLET BALANCE")
    print("-" * 40)
    
    try:
        response = requests.get(f"{BASE_URL}/api/sepay/wallet", headers=headers)
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Wallet Balance: {data.get('balance', 0):,.0f} VND")
            print(f"   Currency: {data.get('currency', 'VND')}")
            print(f"   Status: {data.get('status', 'unknown')}")
            return data.get('balance', 0)
        else:
            print(f"❌ Error: {response.text}")
            return 0
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return 0

def test_wallet_sufficient_payment():
    """
    ✅ Test thanh toán với ví đủ tiền
    
    CÁCH CHẠY:
        python -c "from tests.test_purchase_logic import test_wallet_sufficient_payment; test_wallet_sufficient_payment()"
    
    KẾT QUẢ MONG ĐỢI:
        - Status: "paid" (thanh toán ngay lập tức)
        - Wallet balance giảm
        - License được tạo
    """
    
    print("✅ TEST: Wallet Payment (Sufficient Balance)")
    print("-" * 50)
    
    # Check current balance first
    current_balance = check_wallet_balance()
    
    # 🔄 Adjust price để đảm bảo đủ tiền
    test_price = min(5000, current_balance - 1000) if current_balance > 1000 else 1000
    
    payload = {
        "items": [
            {
                "symbol_id": 671,  # 🔄 Thay đổi symbol_id nếu cần
                "price": test_price,
                "license_days": 7,
                "metadata": {"test": "sufficient_balance"}
            }
        ],
        "payment_method": "wallet",
        "description": f"Test wallet payment - {test_price} VND"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/sepay/symbol/order/create",
            headers=headers,
            json=payload,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "paid":
                print("✅ SUCCESS: Order paid immediately with wallet!")
                print(f"   Order ID: {data.get('order_id')}")
                print(f"   Amount: {data.get('total_amount')} VND")
                
                # Check balance after payment
                print("\n💰 Wallet balance after payment:")
                check_wallet_balance()
            else:
                print(f"⚠️  Order created but status: {data.get('status')}")
                
    except Exception as e:
        print(f"❌ Request failed: {e}")

def test_wallet_insufficient_payment():
    """
    ⏳ Test thanh toán với ví không đủ tiền
    
    CÁCH CHẠY:
        python -c "from tests.test_purchase_logic import test_wallet_insufficient_payment; test_wallet_insufficient_payment()"
    
    KẾT QUẢ MONG ĐỢI:
        - Status: "pending_payment" 
        - Wallet balance không đổi
        - Order chờ payment
    """
    
    print("⏳ TEST: Wallet Payment (Insufficient Balance)")
    print("-" * 50)
    
    # Tạo order với giá cao hơn số dư
    current_balance = check_wallet_balance()
    test_price = current_balance + 10000  # Đảm bảo không đủ tiền
    
    payload = {
        "items": [
            {
                "symbol_id": 671,  # 🔄 Thay đổi symbol_id nếu cần
                "price": test_price,
                "license_days": 30,
                "metadata": {"test": "insufficient_balance"}
            }
        ],
        "payment_method": "wallet",
        "description": f"Test wallet insufficient - {test_price} VND"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/sepay/symbol/order/create",
            headers=headers,
            json=payload,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "pending_payment":
                print("✅ SUCCESS: Order pending due to insufficient balance!")
                print(f"   Order ID: {data.get('order_id')}")
                print(f"   Amount: {data.get('total_amount')} VND")
                return data.get('order_id')
            else:
                print(f"⚠️  Unexpected status: {data.get('status')}")
                
    except Exception as e:
        print(f"❌ Request failed: {e}")
        
    return None

def test_sepay_payment():
    """
    💳 Test thanh toán bằng SePay (tự động tạo QR)
    
    CÁCH CHẠY:
        python -c "from tests.test_purchase_logic import test_sepay_payment; test_sepay_payment()"
    
    KẾT QUẢ MONG ĐỢI:
        - Status: "pending_payment"
        - Có qr_code_url và deep_link
        - Payment intent được tạo
    """
    
    print("💳 TEST: SePay Payment (Auto QR Generation)")
    print("-" * 50)
    
    payload = {
        "items": [
            {
                "symbol_id": 671,  # 🔄 Thay đổi symbol_id nếu cần
                "price": 25000,
                "license_days": 15,
                "metadata": {"test": "sepay_payment"}
            }
        ],
        "payment_method": "sepay_transfer",
        "description": "Test SePay payment with auto QR"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/sepay/symbol/order/create",
            headers=headers,
            json=payload,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("qr_code_url") and data.get("payment_intent_id"):
                print("✅ SUCCESS: SePay QR code generated!")
                print(f"   Order ID: {data.get('order_id')}")
                print(f"   QR Code: {data.get('qr_code_url')}")
                print(f"   Deep Link: {data.get('deep_link')}")
                print(f"   Payment Intent: {data.get('payment_intent_id')}")
                return {
                    'order_id': data.get('order_id'),
                    'payment_intent_id': data.get('payment_intent_id')
                }
            else:
                print("⚠️  QR code not generated")
                
    except Exception as e:
        print(f"❌ Request failed: {e}")
        
    return None

def test_manual_wallet_payment(order_id):
    """
    🔄 Test thanh toán manual bằng ví cho pending order
    
    CÁCH CHẠY:
        python -c "from tests.test_purchase_logic import test_manual_wallet_payment; test_manual_wallet_payment('order_id_here')"
    
    PARAMETERS:
        order_id (str): ID của order đang pending
    """
    
    print(f"🔄 TEST: Manual Wallet Payment for Order {order_id}")
    print("-" * 50)
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/sepay/symbol/order/{order_id}/pay-wallet",
            headers=headers,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "paid":
                print("✅ SUCCESS: Order paid with wallet!")
            else:
                print(f"⚠️  Payment status: {data.get('status')}")
                
    except Exception as e:
        print(f"❌ Request failed: {e}")

def test_order_topup(order_id):
    """
    💰 Test tạo topup SePay cho order không đủ tiền
    
    CÁCH CHẠY:
        python -c "from tests.test_purchase_logic import test_order_topup; test_order_topup('order_id_here')"
    
    PARAMETERS:
        order_id (str): ID của order cần topup
    """
    
    print(f"💰 TEST: SePay Topup for Order {order_id}")
    print("-" * 50)
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/sepay/symbol/order/{order_id}/topup-sepay",
            headers=headers,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ SUCCESS: Topup QR generated!")
            print(f"   QR Code: {data.get('qr_code_url')}")
            print(f"   Amount: {data.get('amount')} VND")
                
    except Exception as e:
        print(f"❌ Request failed: {e}")

def check_order_history():
    """
    📋 Kiểm tra lịch sử orders
    
    CÁCH CHẠY:
        python -c "from tests.test_purchase_logic import check_order_history; check_order_history()"
    """
    
    print("📋 CHECKING ORDER HISTORY")
    print("-" * 40)
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/sepay/symbol/orders/history?page=1&limit=5",
            headers=headers
        )
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            orders = data.get('results', [])
            
            print(f"✅ Found {len(orders)} recent orders:")
            for order in orders:
                print(f"   🔹 {order.get('order_id')}")
                print(f"      Status: {order.get('status')}")
                print(f"      Amount: {order.get('total_amount')} VND")
                print(f"      Method: {order.get('payment_method')}")
                print(f"      Created: {order.get('created_at')}")
                print()
                
    except Exception as e:
        print(f"❌ Request failed: {e}")

def check_user_licenses():
    """
    🎫 Kiểm tra licenses đã mua
    
    CÁCH CHẠY:
        python -c "from tests.test_purchase_logic import check_user_licenses; check_user_licenses()"
    """
    
    print("🎫 CHECKING USER LICENSES")
    print("-" * 40)
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/sepay/symbol/licenses?page=1&limit=10",
            headers=headers
        )
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            licenses = response.json()
            
            print(f"✅ Found {len(licenses)} licenses:")
            for license_data in licenses:
                print(f"   🎫 Symbol ID: {license_data.get('symbol_id')}")
                print(f"      Days: {license_data.get('license_days')}")
                print(f"      Expires: {license_data.get('expires_at')}")
                print(f"      Active: {license_data.get('is_active')}")
                print()
                
    except Exception as e:
        print(f"❌ Request failed: {e}")

def run_full_test_suite():
    """🚀 Chạy tất cả tests theo thứ tự logic"""
    
    print("🚀 RUNNING FULL PURCHASE LOGIC TEST SUITE")
    print("=" * 80)
    
    if JWT_TOKEN == "YOUR_JWT_TOKEN_HERE":
        print("❌ ERROR: Please update JWT_TOKEN in the script first!")
        return
    
    # 1. Check current state
    print("\n1️⃣  CHECKING CURRENT STATE")
    check_wallet_balance()
    check_order_history()
    check_user_licenses()
    
    # 2. Test wallet payment (sufficient)
    print("\n2️⃣  TESTING WALLET PAYMENT (SUFFICIENT)")
    test_wallet_sufficient_payment()
    
    # 3. Test wallet payment (insufficient) 
    print("\n3️⃣  TESTING WALLET PAYMENT (INSUFFICIENT)")
    pending_order_id = test_wallet_insufficient_payment()
    
    # 4. Test SePay payment
    print("\n4️⃣  TESTING SEPAY PAYMENT")
    sepay_result = test_sepay_payment()
    
    # 5. Test topup for insufficient order
    if pending_order_id:
        print(f"\n5️⃣  TESTING TOPUP FOR PENDING ORDER")
        test_order_topup(pending_order_id)
    
    # 6. Check final state
    print("\n6️⃣  CHECKING FINAL STATE")
    check_order_history()
    check_user_licenses()
    
    print("\n✅ FULL TEST SUITE COMPLETED!")
    print("=" * 80)

if __name__ == "__main__":
    print("🛒 SYMBOL PURCHASE LOGIC TESTING")
    print("=" * 60)
    print()
    print("📋 Available Tests:")
    print("  1️⃣  check_wallet_balance() - Kiểm tra số dư ví")
    print("  2️⃣  test_wallet_sufficient_payment() - Test ví đủ tiền")  
    print("  3️⃣  test_wallet_insufficient_payment() - Test ví không đủ")
    print("  4️⃣  test_sepay_payment() - Test thanh toán SePay")
    print("  5️⃣  test_manual_wallet_payment(order_id) - Test pay manual")
    print("  6️⃣  test_order_topup(order_id) - Test topup cho order")
    print("  7️⃣  check_order_history() - Xem lịch sử orders")
    print("  8️⃣  check_user_licenses() - Xem licenses đã mua")
    print("  9️⃣  run_full_test_suite() - Chạy tất cả tests")
    print()
    print("💡 Tips:")
    print("   - Cập nhật JWT_TOKEN trước khi chạy")
    print("   - Thay đổi symbol_id nếu cần")
    print("   - Check server đang chạy tại localhost:8000")
    print()
    
    # Check token
    if JWT_TOKEN == "YOUR_JWT_TOKEN_HERE":
        print("⚠️  WARNING: Please update JWT_TOKEN first!")
        print("   Get token from: POST /api/auth/login")
    else:
        print("🚀 Running basic checks...")
        check_wallet_balance()
        check_order_history()