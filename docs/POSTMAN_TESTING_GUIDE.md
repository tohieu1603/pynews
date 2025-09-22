# Postman Testing Guide - Wallet Topup Flow

Hướng dẫn test luồng nạp tiền ví qua Postman với đầy đủ các bước từ tạo intent đến hoàn tất giao dịch.

## Chuẩn bị

### 1. Environment Variables
Tạo Environment trong Postman với các biến sau:

```json
{
  "base_url": "http://localhost:8000",
  "access_token": "",
  "refresh_token": "",
  "user_id": "",
  "intent_id": "",
  "order_code": "",
  "sepay_tx_id": ""
}
```

### 2. Authentication Headers
Tất cả các request cần header:
```
Authorization: Bearer {{access_token}}
Content-Type: application/json
```

## Bước 1: Đăng nhập (Authentication)

### Request: Login
```http
POST {{base_url}}/api/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "your_password"
}
```

### Response Success:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "username": "testuser",
    "first_name": "Test",
    "last_name": "User"
  }
}
```

### Postman Test Script:
```javascript
if (pm.response.code === 200) {
    const response = pm.response.json();
    pm.environment.set("access_token", response.access_token);
    pm.environment.set("refresh_token", response.refresh_token);
    pm.environment.set("user_id", response.user.id);
    console.log("Authentication successful");
}
```

## Bước 2: Kiểm tra Wallet hiện tại

### Request: Get Current Wallet
```http
GET {{base_url}}/api/seapay/wallet
Authorization: Bearer {{access_token}}
```

### Response Success:
```json
{
  "wallet_id": "123e4567-e89b-12d3-a456-426614174000",
  "balance": 0.00,
  "currency": "VND",
  "status": "active",
  "created_at": "2025-09-22T10:00:00Z",
  "updated_at": "2025-09-22T10:00:00Z"
}
```

## Bước 3: Tạo Wallet Topup Intent

### Request: Create Topup Intent
```http
POST {{base_url}}/api/seapay/wallet/topup/create
Authorization: Bearer {{access_token}}
Content-Type: application/json

{
  "amount": 100000,
  "currency": "VND",
  "bank_code": "BIDV",
  "expires_in_minutes": 60
}
```

### Response Success:
```json
{
  "intent_id": "123e4567-e89b-12d3-a456-426614174001",
  "order_code": "TOPUP_1695369600_A1B2C3D4",
  "amount": 100000,
  "currency": "VND",
  "status": "processing",
  "qr_image_url": "https://api.vietqr.io/image/VCB-1234567890-vietqr.jpg?amount=100000&addInfo=TOPUP_1695369600_A1B2C3D4",
  "account_number": "1234567890",
  "account_name": "CONG TY ABC",
  "transfer_content": "TOPUP_1695369600_A1B2C3D4",
  "bank_code": "VCB",
  "expires_at": "2025-09-22T11:00:00Z",
  "message": "Topup request created successfully. Please scan QR code to complete payment."
}
```

### Postman Test Script:
```javascript
if (pm.response.code === 200) {
    const response = pm.response.json();
    pm.environment.set("intent_id", response.intent_id);
    pm.environment.set("order_code", response.order_code);
    console.log("Topup intent created:", response.intent_id);
    console.log("Order code:", response.order_code);
    console.log("QR URL:", response.qr_image_url);
}
```

## Bước 4: Kiểm tra trạng thái Topup

### Request: Get Topup Status
```http
GET {{base_url}}/api/seapay/wallet/topup/{{intent_id}}/status
Authorization: Bearer {{access_token}}
```

### Response Success (Pending):
```json
{
  "intent_id": "123e4567-e89b-12d3-a456-426614174001",
  "order_code": "TOPUP_1695369600_A1B2C3D4",
  "amount": 100000,
  "status": "processing",
  "is_expired": false,
  "qr_image_url": "https://api.vietqr.io/image/VCB-1234567890-vietqr.jpg?amount=100000&addInfo=TOPUP_1695369600_A1B2C3D4",
  "account_number": "1234567890",
  "account_name": "CONG TY ABC",
  "transfer_content": "TOPUP_1695369600_A1B2C3D4",
  "bank_code": "VCB",
  "expires_at": "2025-09-22T11:00:00Z",
  "payment_id": null,
  "provider_payment_id": null,
  "balance_before": null,
  "balance_after": null,
  "completed_at": null,
  "message": "Topup status: processing"
}
```

## Bước 5: Mô phỏng SePay Webhook (Test)

### Request: SePay Webhook Simulation
```http
POST {{base_url}}/api/seapay/webhook/sepay
Content-Type: application/json

{
  "id": 987654321,
  "gateway": "VCB",
  "transactionDate": "2025-09-22T10:30:00Z",
  "accountNumber": "1234567890",
  "subAccount": "",
  "code": "VCB",
  "content": "{{order_code}}",
  "transferType": "in",
  "description": "Nap tien vi",
  "transferAmount": 100000,
  "referenceCode": "REF123456789"
}
```

### Response Success:
```json
{
  "status": "success",
  "message": "Topup completed successfully",
  "payment_id": "123e4567-e89b-12d3-a456-426614174002",
  "processed_at": "2025-09-22T10:30:05Z"
}
```

### Postman Test Script:
```javascript
if (pm.response.code === 200) {
    const response = pm.response.json();
    pm.environment.set("sepay_tx_id", "987654321");
    console.log("Webhook processed:", response.status);
    console.log("Payment ID:", response.payment_id);
}
```

## Bước 6: Kiểm tra trạng thái sau khi thanh toán

### Request: Get Topup Status After Payment
```http
GET {{base_url}}/api/seapay/wallet/topup/{{intent_id}}/status
Authorization: Bearer {{access_token}}
```

### Response Success (Completed):
```json
{
  "intent_id": "123e4567-e89b-12d3-a456-426614174001",
  "order_code": "TOPUP_1695369600_A1B2C3D4",
  "amount": 100000,
  "status": "succeeded",
  "is_expired": false,
  "qr_image_url": "https://api.vietqr.io/image/VCB-1234567890-vietqr.jpg?amount=100000&addInfo=TOPUP_1695369600_A1B2C3D4",
  "account_number": "1234567890",
  "account_name": "CONG TY ABC",
  "transfer_content": "TOPUP_1695369600_A1B2C3D4",
  "bank_code": "VCB",
  "expires_at": "2025-09-22T11:00:00Z",
  "payment_id": "123e4567-e89b-12d3-a456-426614174002",
  "provider_payment_id": "987654321",
  "balance_before": 0.00,
  "balance_after": 100000.00,
  "completed_at": "2025-09-22T10:30:00Z",
  "message": "Topup status: succeeded"
}
```

## Bước 7: Kiểm tra Wallet sau khi nạp tiền

### Request: Get Updated Wallet Balance
```http
GET {{base_url}}/api/seapay/wallet
Authorization: Bearer {{access_token}}
```

### Response Success:
```json
{
  "wallet_id": "123e4567-e89b-12d3-a456-426614174000",
  "balance": 100000.00,
  "currency": "VND",
  "status": "active",
  "created_at": "2025-09-22T10:00:00Z",
  "updated_at": "2025-09-22T10:30:05Z"
}
```

## Bước 8: Xem lịch sử nạp tiền

### Request: Get Topup History
```http
GET {{base_url}}/api/seapay/wallet/topup/history?page=1&limit=10
Authorization: Bearer {{access_token}}
```

### Response Success:
```json
{
  "results": [
    {
      "intent_id": "123e4567-e89b-12d3-a456-426614174001",
      "order_code": "TOPUP_1695369600_A1B2C3D4",
      "amount": 100000,
      "status": "succeeded",
      "expires_at": "2025-09-22T11:00:00Z",
      "is_expired": false,
      "created_at": "2025-09-22T10:00:00Z",
      "qr_image_url": "https://api.vietqr.io/image/VCB-1234567890-vietqr.jpg?amount=100000&addInfo=TOPUP_1695369600_A1B2C3D4",
      "payment_id": "123e4567-e89b-12d3-a456-426614174002",
      "completed_at": "2025-09-22T10:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 1,
    "pages": 1,
    "has_next": false,
    "has_previous": false
  }
}
```

## Test Cases nâng cao

### Test Case 1: Hủy topup
```http
POST {{base_url}}/api/seapay/wallet/topup/{{intent_id}}/cancel
Authorization: Bearer {{access_token}}
```

### Test Case 2: Topup với số tiền không hợp lệ
```http
POST {{base_url}}/api/seapay/wallet/topup/create
Authorization: Bearer {{access_token}}
Content-Type: application/json

{
  "amount": -1000,
  "currency": "VND",
  "bank_code": "VCB"
}
```

### Test Case 3: Webhook với content không khớp
```http
POST {{base_url}}/api/seapay/webhook/sepay
Content-Type: application/json

{
  "id": 987654322,
  "content": "INVALID_ORDER_CODE",
  "transferAmount": 100000,
  "transferType": "in"
}
```

## Postman Collection Structure

```
📁 Wallet Topup Flow
├── 📁 01. Authentication
│   ├── Login
│   └── Refresh Token
├── 📁 02. Wallet Management
│   ├── Get Current Wallet
│   └── Get Wallet History
├── 📁 03. Topup Flow
│   ├── Create Topup Intent
│   ├── Get Topup Status
│   ├── Cancel Topup
│   └── Get Topup History
├── 📁 04. Webhook Simulation
│   ├── SePay Webhook Success
│   ├── SePay Webhook Invalid Content
│   └── SePay Webhook Invalid Amount
└── 📁 05. Error Cases
    ├── Unauthorized Request
    ├── Invalid Amount
    ├── Expired Intent
    └── Suspended Wallet
```

## Automated Testing Script

### Pre-request Script (Collection Level):
```javascript
// Set current timestamp
pm.globals.set("timestamp", new Date().toISOString());

// Log request info
console.log("Making request to:", pm.request.url.toString());
```

### Test Script (Collection Level):
```javascript
// Log response
console.log("Response status:", pm.response.code);
console.log("Response time:", pm.response.responseTime + "ms");

// Common assertions
pm.test("Response time is less than 2000ms", function () {
    pm.expect(pm.response.responseTime).to.be.below(2000);
});

pm.test("Content-Type is application/json", function () {
    pm.expect(pm.response.headers.get("Content-Type")).to.include("application/json");
});
```

## Monitoring và Debugging

### Environment Variables cho Debug:
```json
{
  "debug_mode": true,
  "log_level": "verbose",
  "timeout": 30000
}
```

### Error Response Examples:

**400 Bad Request:**
```json
{
  "error": "Amount must be greater than 0",
  "detail": "Invalid amount provided"
}
```

**401 Unauthorized:**
```json
{
  "error": "Authentication credentials were not provided"
}
```

**404 Not Found:**
```json
{
  "error": "Topup intent not found"
}
```

**500 Internal Server Error:**
```json
{
  "error": "Failed to create topup request: Database connection error"
}
```

## Checklist Validation

### ✅ Trước khi test:
- [ ] Server Django đang chạy
- [ ] Database đã migrate
- [ ] User đã được tạo và có thể login
- [ ] Environment variables đã được set

### ✅ Trong quá trình test:
- [ ] Access token hợp lệ
- [ ] Response status codes đúng
- [ ] Response data structure đúng
- [ ] Environment variables được update

### ✅ Sau khi test:
- [ ] Wallet balance được cập nhật đúng
- [ ] Database records được tạo
- [ ] Logs không có errors
- [ ] All test assertions pass