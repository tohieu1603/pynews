# Bot Purchase System - Hệ thống mua bot

Hệ thống cho phép user mua bot với 2 phương thức thanh toán: ví (wallet) hoặc chuyển khoản qua SePay.

## 📊 Database Schema

### Tables

#### `pay_bot_orders`
- **order_id** (UUID, PK): ID đơn hàng
- **user_id** (BIGINT): User mua bot  
- **total_amount** (DECIMAL): Tổng tiền cần trả
- **status** (VARCHAR): pending_payment | paid | failed | cancelled | refunded
- **payment_method** (VARCHAR): wallet | sepay_transfer
- **description** (TEXT): Mô tả đơn hàng
- **payment_intent_id** (UUID): Liên kết với PayPaymentIntent khi dùng SePay
- **created_at**, **updated_at**

#### `pay_bot_order_items`
- **order_item_id** (UUID, PK): ID item
- **order_id** (UUID): Đơn hàng chính
- **symbol_id** (BIGINT): Bot được mua
- **price** (DECIMAL): Đơn giá tại thời điểm mua
- **license_days** (INT): Số ngày license (NULL = trọn đời)
- **metadata** (JSON): Thuộc tính bổ sung

#### `pay_user_bot_licenses`
- **license_id** (UUID, PK): ID license
- **user_id** (BIGINT): User được cấp quyền
- **symbol_id** (BIGINT): Bot được cấp quyền
- **order_id** (UUID): Đơn hàng tạo ra license
- **status** (VARCHAR): active | expired | suspended | revoked
- **start_at** (TIMESTAMP): Thời điểm kích hoạt
- **end_at** (TIMESTAMP): Thời điểm hết hạn (NULL = trọn đời)
- **created_at**

#### `pay_wallet_ledger` (Updated)
- Thêm **order_id** (UUID): Liên kết đơn hàng khi là purchase/refund
- **tx_type**: deposit | purchase | refund | withdrawal | transfer_in | transfer_out
- **note**: Diễn giải ngắn gọn

## 🔄 Luồng mua bot

### 1. Tạo đơn hàng
```http
POST /api/seapay/bot/order/create
{
  "items": [
    {
      "symbol_id": 1,
      "price": 500000,
      "license_days": 30,
      "metadata": {"version": "v1.0"}
    }
  ],
  "payment_method": "wallet", // hoặc "sepay_transfer"
  "description": "Mua Bot Trading A"
}
```

**Response:**
```json
{
  "order_id": "123e4567-e89b-12d3-a456-426614174000",
  "total_amount": 500000,
  "status": "pending_payment",
  "payment_method": "wallet",
  "items": [...],
  "created_at": "2025-09-22T10:00:00Z",
  "message": "Order created successfully. Total: 500000 VND"
}
```

### 2A. Thanh toán bằng ví
```http
POST /api/seapay/bot/order/{order_id}/pay-wallet
```

**Response:**
```json
{
  "success": true,
  "message": "Payment processed successfully",
  "order_id": "123e4567-e89b-12d3-a456-426614174000",
  "amount_charged": 500000,
  "wallet_balance_after": 1500000,
  "licenses_created": 1
}
```

### 2B. Thanh toán bằng SePay
```http
POST /api/seapay/bot/order/{order_id}/pay-sepay
```

**Response:**
```json
{
  "intent_id": "456e7890-e89b-12d3-a456-426614174001", 
  "order_code": "TOPUP1727001234ABCD",
  "amount": 500000,
  "currency": "VND",
  "expires_at": "2025-09-22T11:00:00Z",
  "qr_code_url": "https://qr.sepay.vn/img?acc=96247CISI1&bank=BIDV&amount=500000&des=TOPUP1727001234ABCD&template=compact",
  "message": "Payment intent created. Please scan QR code to complete payment."
}
```

### 3. Cấp license tự động

Sau khi thanh toán thành công:

1. **Cập nhật order status** → `paid`
2. **Tạo license** trong `pay_user_bot_licenses`:
   - `user_id`: User mua
   - `symbol_id`: Bot được mua  
   - `start_at`: now()
   - `end_at`: now() + license_days (hoặc NULL nếu trọn đời)
   - `status`: active

3. **Ghi ledger** (chỉ với wallet payment):
   - `tx_type`: purchase
   - `is_credit`: false (trừ tiền)
   - `order_id`: liên kết đơn hàng

## 🔍 API Endpoints

### Quản lý đơn hàng

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/seapay/bot/order/create` | Tạo đơn hàng mua bot |
| POST | `/api/seapay/bot/order/{id}/pay-wallet` | Thanh toán bằng ví |
| POST | `/api/seapay/bot/order/{id}/pay-sepay` | Tạo payment intent SePay |
| GET | `/api/seapay/bot/orders/history` | Lịch sử mua hàng |

### Quản lý license

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/seapay/bot/{symbol_id}/access` | Kiểm tra quyền truy cập bot |
| GET | `/api/seapay/bot/licenses` | Danh sách license của user |

## 🎯 Kiểm tra quyền truy cập

```http
GET /api/seapay/bot/123/access
```

**Response:**
```json
{
  "has_access": true,
  "license_id": "789e0123-e89b-12d3-a456-426614174002",
  "start_at": "2025-09-22T10:00:00Z",
  "end_at": "2025-10-22T10:00:00Z", // NULL nếu trọn đời
  "is_lifetime": false,
  "expires_soon": false // true nếu còn <= 7 ngày
}
```

## 📋 Lịch sử mua hàng

```http
GET /api/seapay/bot/orders/history?page=1&limit=10
```

**Response:**
```json
{
  "results": [
    {
      "order_id": "123e4567-e89b-12d3-a456-426614174000",
      "total_amount": 500000,
      "status": "paid",
      "payment_method": "wallet",
      "description": "Mua Bot Trading A",
      "created_at": "2025-09-22T10:00:00Z",
      "items": [
        {
          "symbol_id": 1,
          "price": 500000,
          "license_days": 30,
          "metadata": {"version": "v1.0"}
        }
      ]
    }
  ],
  "total": 5,
  "page": 1,
  "limit": 10
}
```

## 🔧 Service Layer

### BotPurchaseService

#### Phương thức chính:

- **`create_bot_order()`**: Tạo đơn hàng và items
- **`process_wallet_payment()`**: Xử lý thanh toán ví
- **`create_sepay_payment_intent()`**: Tạo payment intent SePay
- **`process_sepay_payment_completion()`**: Xử lý khi SePay hoàn tất
- **`check_user_bot_access()`**: Kiểm tra quyền truy cập
- **`get_user_bot_licenses()`**: Lấy danh sách license
- **`get_user_order_history()`**: Lịch sử mua hàng

#### License Management:

- **Extend license**: Nếu user đã có license active cho bot, extend thời gian thay vì tạo mới
- **Lifetime upgrade**: License mới là lifetime sẽ override license có thời hạn
- **Multiple symbols**: Một order có thể chứa nhiều bot khác nhau

## 🔒 Quy tắc business

### Wallet Payment:
- Phải có đủ số dư trong ví
- Ghi ledger với `tx_type = purchase`
- Cập nhật wallet balance ngay lập tức

### SePay Payment:
- Tạo PayPaymentIntent với `purpose = order_payment`
- Webhook callback sẽ trigger license creation
- Timeout theo expires_at của intent

### License Rules:
- Một user có thể có nhiều license cho các bot khác nhau
- License active có thể extend bằng việc mua thêm
- License lifetime (end_at = NULL) không thể bị override
- License hết hạn tự động chuyển status thành expired

## 🧪 Testing

### Test Scenarios:

1. **Wallet Payment Flow**:
   - Tạo order → Pay wallet → Verify license created
   - Insufficient balance → Error
   - Extend existing license

2. **SePay Payment Flow**:
   - Tạo order → Create intent → Webhook callback → Verify license

3. **License Management**:
   - Check access for active license
   - Check access for expired license  
   - Multiple licenses per user

4. **Error Handling**:
   - Invalid symbol_id
   - Order not found
   - Payment failures

### Sample Test Data:

```python
# Tạo test order
order_data = {
    "items": [
        {
            "symbol_id": 1,
            "price": 500000,
            "license_days": 30
        }
    ],
    "payment_method": "wallet",
    "description": "Test order"
}

# Check license after payment
access = bot_purchase_service.check_user_bot_access(user, symbol_id=1)
assert access['has_access'] == True
assert access['is_lifetime'] == False
```

## 📈 Monitoring

### Key Metrics:
- Số đơn hàng tạo / ngày
- Tỷ lệ conversion (order → paid)
- Phương thức thanh toán phổ biến
- Top bot được mua nhiều nhất
- Revenue theo thời gian

### Logging:
- Order creation, payment, license assignment
- Failed payments và nguyên nhân
- License expiration warnings
- Wallet balance changes

## 🚀 Deployment Notes

1. **Migration Order**: Chạy migration cho models mới
2. **Indexing**: Đảm bảo indexes cho performance
3. **Monitoring**: Setup alerts cho failed payments
4. **Backup**: Backup trước khi deploy major changes