#!/usr/bin/env python3
"""
Script test API mua symbol
"""
import requests
import json

# Cấu hình
BASE_URL = "http://localhost:8000"
JWT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoyLCJlbWFpbCI6ImhpZXV0dHBoNDc2MzlAZnB0LmVkdS52biIsImlhdCI6MTc1ODUyNTY2NCwiZXhwIjoxNzU4NTI5MjY0LCJ0eXBlIjoiYWNjZXNzIn0.xh2C-G9EGB9eQh77UneETvYMTwlQJTLIc0cFzEYRDFk"

headers = {
    "Authorization": f"Bearer {JWT_TOKEN}",
    "Content-Type": "application/json"
}

def test_create_order():
    """Test tạo đơn hàng mua symbol"""
    print("🛒 TEST 1: Tạo đơn hàng mua symbol")
    print("-" * 50)
    
    # Test case 1: Đơn hàng hợp lệ (8k - trong phạm vi số dư 10k)
    payload = {
        "items": [
            {
                "symbol_id": 888,
                "price": 8000,
                "license_days": 10,
                "metadata": {
                    "package": "test",
                    "note": "API test purchase"
                }
            }
        ],
        "payment_method": "wallet",
        "description": "Test mua symbol qua API"
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
        
        if response.status_code == 200:  # API trả về 200, không phải 201
            return response.json().get("order_id")
        elif response.status_code == 400:
            print("❌ Lỗi validation - có thể do số dư không đủ")
        else:
            print(f"❌ Lỗi: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")
        
    return None

def test_invalid_order():
    """Test tạo đơn hàng với số dư không đủ"""
    print("\n🚫 TEST 2: Tạo đơn hàng vượt quá số dư")
    print("-" * 50)
    
    payload = {
        "items": [
            {
                "symbol_id": 999,
                "price": 50000,  # Vượt quá số dư 10k
                "license_days": 30
            }
        ],
        "payment_method": "wallet",
        "description": "Test đơn hàng vượt số dư"
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
        
    except Exception as e:
        print(f"❌ Error: {e}")

def test_wallet_payment(order_id):
    """Test thanh toán đơn hàng bằng ví"""
    if not order_id:
        print("\n⏭️ Bỏ qua test thanh toán vì không có order_id")
        return
        
    print(f"\n💳 TEST 3: Thanh toán đơn hàng {order_id}")
    print("-" * 50)
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/sepay/symbol/order/{order_id}/pay-wallet",
            headers=headers,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

def test_wallet_info():
    """Test lấy thông tin ví"""
    print(f"\n💰 TEST 4: Kiểm tra thông tin ví")
    print("-" * 50)
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/sepay/wallet",
            headers=headers,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🚀 Bắt đầu test API Symbol Purchase")
    print(f"Server: {BASE_URL}")
    print(f"Token: {JWT_TOKEN[:50]}...")
    print("=" * 70)
    
    # Test 1: Tạo đơn hàng hợp lệ
    order_id = test_create_order()
    
    # Test 2: Tạo đơn hàng không hợp lệ
    test_invalid_order()
    
    # Test 3: Thanh toán nếu có order_id
    test_wallet_payment(order_id)
    
    # Test 4: Kiểm tra ví
    test_wallet_info()
    
    print("\n✅ Hoàn thành test API!")