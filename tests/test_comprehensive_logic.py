#!/usr/bin/env python3
"""
🧪 Comprehensive Symbol Purchase Logic Test

CÁCH SỬ DỤNG:
1. Cập nhật TOKEN với JWT token hợp lệ
2. Chạy: python tests/test_comprehensive_logic.py
3. Hoặc chạy từng scenario riêng biệt

MỤC ĐÍCH:
- Test toàn bộ logic mua symbol trong các scenarios khác nhau
- Verify tất cả payment methods và edge cases
- End-to-end testing cho payment flow

SCENARIOS:
1. Wallet sufficient → Immediate payment
2. Wallet insufficient → Pending order  
3. SePay payment → QR generation
4. Manual wallet payment for pending order
5. Topup scenarios

REQUIREMENTS:
- Server chạy tại localhost:8000
- JWT token hợp lệ
- Test symbols trong database
"""

import requests
import json
import time

# 🔄 CẬP NHẬT TOKEN
BASE_URL = "http://localhost:8000"
TOKEN = "YOUR_JWT_TOKEN_HERE"  # 🔄 Thay đổi JWT token ở đây

def get_headers():
    """Get request headers with auth"""
    return {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

def check_wallet_balance():
    """
    💰 Check current wallet balance
    
    Returns:
        float: Current balance in VND
    """
    response = requests.get(f"{BASE_URL}/api/sepay/wallet", headers=get_headers())
    if response.status_code == 200:
        balance = response.json()['balance']
        print(f"💰 Current wallet balance: {balance:,.0f} VND")
        return float(balance)
    else:
        print(f"❌ Error checking wallet: {response.text}")
        return 0

def test_scenario_1_wallet_sufficient():
    """
    ✅ TEST 1: payment_method=wallet with sufficient balance
    
    EXPECTED RESULT:
        - Order status: "paid" immediately
        - Wallet balance decreased
        - License created for user
    """
    print("\n" + "="*60)
    print("🧪 TEST 1: Wallet payment with sufficient balance")
    print("Expected: Order should be PAID immediately")
    print("="*60)
    
    current_balance = check_wallet_balance()
    test_price = min(1000, current_balance - 500) if current_balance > 500 else 500
    
    order_data = {
        "items": [
            {
                "symbol_id": 671,  # 🔄 Thay symbol_id nếu cần
                "price": test_price,
                "license_days": 30,
                "metadata": {"test_scenario": "wallet_sufficient"}
            }
        ],
        "payment_method": "wallet",
        "description": f"Test wallet payment - sufficient balance ({test_price} VND)"
    }
    
    response = requests.post(f"{BASE_URL}/api/sepay/symbol/order/create", 
                           json=order_data, headers=get_headers())
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Order created: {data['order_id']}")
        print(f"📊 Order status: {data['status']}")
        print(f"💰 Total amount: {data['total_amount']} VND")
        
        if data['status'] == 'paid':
            print("🎉 SUCCESS: Order paid immediately with wallet!")
            
            # Check balance after
            new_balance = check_wallet_balance()
            print(f"💸 Balance change: {current_balance - new_balance:,.0f} VND deducted")
        else:
            print(f"⚠️  Unexpected status: {data['status']}")
            
        return data['order_id']
    else:
        print(f"❌ Order creation failed: {response.text}")
        return None

def test_scenario_2_wallet_insufficient():
    """
    ⏳ TEST 2: payment_method=wallet with insufficient balance
    
    EXPECTED RESULT:
        - Order status: "pending_payment"
        - Wallet balance unchanged
        - No license created yet
    """
    print("\n" + "="*60)
    print("🧪 TEST 2: Wallet payment with insufficient balance")
    print("Expected: Order should be PENDING")
    print("="*60)
    
    current_balance = check_wallet_balance()
    test_price = current_balance + 5000  # Ensure insufficient
    
    order_data = {
        "items": [
            {
                "symbol_id": 671,  # 🔄 Thay symbol_id nếu cần
                "price": test_price,
                "license_days": 30,
                "metadata": {"test_scenario": "wallet_insufficient"}
            }
        ],
        "payment_method": "wallet",
        "description": f"Test wallet payment - insufficient balance ({test_price} VND)"
    }
    
    response = requests.post(f"{BASE_URL}/api/sepay/symbol/order/create", 
                           json=order_data, headers=get_headers())
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Order created: {data['order_id']}")
        print(f"📊 Order status: {data['status']}")
        print(f"💰 Total amount: {data['total_amount']} VND")
        
        if data['status'] == 'pending_payment':
            print("🎉 SUCCESS: Order pending due to insufficient balance!")
            
            # Verify balance unchanged
            new_balance = check_wallet_balance()
            if abs(current_balance - new_balance) < 1:
                print("✅ Wallet balance unchanged (as expected)")
            else:
                print("⚠️  Wallet balance changed unexpectedly")
        else:
            print(f"⚠️  Unexpected status: {data['status']}")
            
        return data['order_id']
    else:
        print(f"❌ Order creation failed: {response.text}")
        return None

def test_scenario_3_sepay_payment():
    """
    💳 TEST 3: payment_method=sepay_transfer
    
    EXPECTED RESULT:
        - Order status: "pending_payment"
        - QR code generated automatically
        - Payment intent created
        - Deep link available
    """
    print("\n" + "="*60)
    print("🧪 TEST 3: SePay payment with auto QR generation")
    print("Expected: Order PENDING with QR code")
    print("="*60)
    
    order_data = {
        "items": [
            {
                "symbol_id": 671,  # 🔄 Thay symbol_id nếu cần
                "price": 15000,
                "license_days": 30,
                "metadata": {"test_scenario": "sepay_payment"}
            }
        ],
        "payment_method": "sepay_transfer",
        "description": "Test SePay payment with auto QR generation"
    }
    
    response = requests.post(f"{BASE_URL}/api/sepay/symbol/order/create", 
                           json=order_data, headers=get_headers())
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Order created: {data['order_id']}")
        print(f"📊 Order status: {data['status']}")
        print(f"💰 Total amount: {data['total_amount']} VND")
        
        if data.get('qr_code_url'):
            print("🎉 SUCCESS: QR code generated automatically!")
            print(f"📱 QR Code URL: {data['qr_code_url']}")
            print(f"🔗 Deep Link: {data.get('deep_link', 'N/A')}")
            print(f"💳 Payment Intent: {data.get('payment_intent_id', 'N/A')}")
        else:
            print("⚠️  QR code not generated")
            
        return {
            'order_id': data['order_id'],
            'payment_intent_id': data.get('payment_intent_id')
        }
    else:
        print(f"❌ Order creation failed: {response.text}")
        return None

def test_scenario_4_manual_wallet_payment(order_id):
    """
    🔄 TEST 4: Manual wallet payment for pending order
    
    PARAMETERS:
        order_id (str): ID của order đang pending
    
    EXPECTED RESULT:
        - Order status: pending_payment → paid
        - Wallet balance decreased
        - License created
    """
    if not order_id:
        print("❌ No order ID provided for manual payment test")
        return
        
    print("\n" + "="*60)
    print(f"🧪 TEST 4: Manual wallet payment for order {order_id}")
    print("Expected: Order should be PAID with wallet")
    print("="*60)
    
    current_balance = check_wallet_balance()
    
    response = requests.post(f"{BASE_URL}/api/sepay/symbol/order/{order_id}/pay-wallet", 
                           headers=get_headers())
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Payment processed!")
        print(f"📊 Result: {json.dumps(data, indent=2, ensure_ascii=False)}")
        
        if data.get('status') == 'paid':
            print("🎉 SUCCESS: Order paid with wallet!")
            
            # Check balance after
            new_balance = check_wallet_balance()
            print(f"💸 Balance change: {current_balance - new_balance:,.0f} VND")
        else:
            print(f"⚠️  Payment status: {data.get('status')}")
            
    elif response.status_code == 400:
        print(f"⚠️  Payment failed (expected if insufficient balance): {response.json().get('detail')}")
    else:
        print(f"❌ Payment request failed: {response.text}")

def test_scenario_5_order_topup(order_id):
    """
    💰 TEST 5: Create SePay topup for pending order
    
    PARAMETERS:
        order_id (str): ID của order cần topup
    
    EXPECTED RESULT:
        - Topup QR code generated
        - User can scan to add funds
        - After payment, can retry wallet payment
    """
    if not order_id:
        print("❌ No order ID provided for topup test")
        return
        
    print("\n" + "="*60)
    print(f"🧪 TEST 5: SePay topup for order {order_id}")
    print("Expected: Topup QR code generated")
    print("="*60)
    
    response = requests.post(f"{BASE_URL}/api/sepay/symbol/order/{order_id}/topup-sepay", 
                           headers=get_headers())
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Topup created!")
        print(f"📱 QR Code: {data.get('qr_code_url', 'N/A')}")
        print(f"💰 Topup Amount: {data.get('amount', 'N/A')} VND")
        print(f"💳 Payment Intent: {data.get('payment_intent_id', 'N/A')}")
        print("🎉 SUCCESS: User can scan QR to topup wallet!")
        
    else:
        print(f"❌ Topup creation failed: {response.text}")

def check_final_state():
    """
    📋 Check final state after all tests
    
    Shows:
        - Current wallet balance
        - Recent orders
        - User licenses
    """
    print("\n" + "="*60)
    print("📋 FINAL STATE CHECK")
    print("="*60)
    
    # Check wallet
    check_wallet_balance()
    
    # Check recent orders
    print("\n📊 Recent Orders:")
    response = requests.get(f"{BASE_URL}/api/sepay/symbol/orders/history?limit=5", 
                          headers=get_headers())
    if response.status_code == 200:
        orders = response.json().get('results', [])
        for order in orders:
            print(f"  🔹 {order['order_id']} - {order['status']} - {order['total_amount']} VND")
    
    # Check licenses
    print("\n🎫 User Licenses:")
    response = requests.get(f"{BASE_URL}/api/sepay/symbol/licenses?limit=5", 
                          headers=get_headers())
    if response.status_code == 200:
        licenses = response.json()
        for license_data in licenses:
            print(f"  🎫 Symbol {license_data['symbol_id']} - {license_data['license_days']} days - Active: {license_data['is_active']}")

def run_comprehensive_test():
    """
    🚀 Run all test scenarios in sequence
    
    FULL TEST FLOW:
        1. Check initial state
        2. Test wallet sufficient payment
        3. Test wallet insufficient payment  
        4. Test SePay payment with QR
        5. Test manual wallet payment
        6. Test order topup
        7. Check final state
    """
    print("🚀 COMPREHENSIVE SYMBOL PURCHASE TEST SUITE")
    print("=" * 80)
    
    if TOKEN == "YOUR_JWT_TOKEN_HERE":
        print("❌ ERROR: Please update TOKEN in the script first!")
        return
    
    # Initial state
    print("\n🔍 INITIAL STATE")
    check_wallet_balance()
    
    # Test scenarios
    paid_order_id = test_scenario_1_wallet_sufficient()
    pending_order_id = test_scenario_2_wallet_insufficient()
    sepay_result = test_scenario_3_sepay_payment()
    
    # Manual payments (if orders created)
    if pending_order_id:
        test_scenario_4_manual_wallet_payment(pending_order_id)
        test_scenario_5_order_topup(pending_order_id)
    
    # Final state
    check_final_state()
    
    print("\n✅ COMPREHENSIVE TEST COMPLETED!")
    print("=" * 80)
    
    # Summary
    print("\n📋 TEST SUMMARY:")
    print(f"   ✅ Wallet sufficient: {'PASSED' if paid_order_id else 'FAILED'}")
    print(f"   ⏳ Wallet insufficient: {'PASSED' if pending_order_id else 'FAILED'}")
    print(f"   💳 SePay payment: {'PASSED' if sepay_result else 'FAILED'}")
    
def test_individual_scenario(scenario_number):
    """
    🎯 Run individual test scenario
    
    PARAMETERS:
        scenario_number (int): 1-5 để chạy test cụ thể
    """
    scenarios = {
        1: test_scenario_1_wallet_sufficient,
        2: test_scenario_2_wallet_insufficient,
        3: test_scenario_3_sepay_payment,
        # 4 and 5 require order_id parameter
    }
    
    if scenario_number in scenarios:
        print(f"🎯 Running Test Scenario {scenario_number}")
        return scenarios[scenario_number]()
    else:
        print(f"❌ Invalid scenario number: {scenario_number}")
        print("Available scenarios: 1, 2, 3")

if __name__ == "__main__":
    print("🧪 COMPREHENSIVE SYMBOL PURCHASE LOGIC TEST")
    print("=" * 70)
    print()
    print("📋 Available Tests:")
    print("  1️⃣  test_scenario_1_wallet_sufficient() - Ví đủ tiền")
    print("  2️⃣  test_scenario_2_wallet_insufficient() - Ví không đủ")
    print("  3️⃣  test_scenario_3_sepay_payment() - Thanh toán SePay")
    print("  4️⃣  test_scenario_4_manual_wallet_payment(order_id) - Pay manual")
    print("  5️⃣  test_scenario_5_order_topup(order_id) - Topup order")
    print("  6️⃣  run_comprehensive_test() - Chạy tất cả scenarios")
    print("  7️⃣  test_individual_scenario(1-3) - Chạy scenario riêng")
    print("  8️⃣  check_final_state() - Kiểm tra trạng thái cuối")
    print()
    print("💡 Usage Tips:")
    print("   - Update TOKEN first!")
    print("   - Ensure server running at localhost:8000")
    print("   - Check symbol_id 671 exists in database")
    print("   - Monitor wallet balance changes")
    print()
    
    if TOKEN == "YOUR_JWT_TOKEN_HERE":
        print("⚠️  WARNING: Please update TOKEN first!")
        print("   Get token from: POST /api/auth/login")
    else:
        print("🚀 Running quick check...")
        check_wallet_balance()
        
        print("\n▶️  To run full test suite: run_comprehensive_test()")
        print("▶️  To run specific test: test_individual_scenario(1-3)")