# Wallet Topup Flow Documentation

## Tổng quan

Hệ thống nạp tiền ví được thiết kế theo luồng 5 bước chính:

1. **Tạo Intent** - Ghi nhận yêu cầu nạp ví
2. **Tạo Attempt** - Sinh QR code để user thanh toán  
3. **Webhook/BankTx** - Nhận thông báo từ SePay
4. **Chốt Payment** - Tạo bản ghi payment
5. **Ghi Ledger** - Cập nhật số dư ví (nguồn sự thật)

## Kiến trúc Database

### Bảng chính

- **pay_payment_intents** - Yêu cầu thanh toán
- **pay_payment_attempts** - Lần thử thanh toán (QR code)
- **pay_payments** - Bản ghi thanh toán đã chốt
- **pay_sepay_webhook_events** - Webhook events từ SePay
- **pay_bank_transactions** - Giao dịch ngân hàng để đối soát
- **pay_wallet_ledger** - Nguồn sự thật cho giao dịch ví
- **pay_wallets** - Cache số dư ví hiện tại

### Mối quan hệ

```
PayPaymentIntent (1) -> (N) PayPaymentAttempt
PayPaymentIntent (1) -> (N) PayPayment  
PayPayment (1) -> (N) PayWalletLedger
PayWallet (1) -> (N) PayWalletLedger
```

## API Endpoints

### 1. Tạo yêu cầu nạp tiền

```http
POST /api/seapay/wallet/topup/create
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "amount": 100000,
  "currency": "VND", 
  "bank_code": "VCB",
  "expires_in_minutes": 60
}
```

**Response:**
```json
{
  "intent_id": "uuid",
  "order_code": "TOPUP_1727001234_ABCD", 
  "amount": 100000,
  "currency": "VND",
  "status": "processing",
  "qr_image_url": "https://api.vietqr.io/...",
  "account_number": "1234567890",
  "account_name": "CONG TY ABC",
  "transfer_content": "TOPUP_1727001234_ABCD",
  "bank_code": "VCB",
  "expires_at": "2025-09-22T11:30:00Z",
  "message": "Topup request created successfully..."
}
```

### 2. Kiểm tra trạng thái nạp tiền

```http
GET /api/seapay/wallet/topup/{intent_id}/status
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "intent_id": "uuid",
  "order_code": "TOPUP_1727001234_ABCD",
  "amount": 100000,
  "status": "succeeded",
  "is_expired": false,
  "qr_image_url": "https://api.vietqr.io/...",
  "account_number": "1234567890", 
  "account_name": "CONG TY ABC",
  "transfer_content": "TOPUP_1727001234_ABCD",
  "bank_code": "VCB",
  "expires_at": "2025-09-22T11:30:00Z",
  "payment_id": "payment_uuid",
  "provider_payment_id": "123456789",
  "balance_before": 0,
  "balance_after": 100000,
  "completed_at": "2025-09-22T10:45:00Z",
  "message": "Topup status: succeeded"
}
```

### 3. Webhook từ SePay

```http
POST /api/seapay/wallet/webhook/sepay
Content-Type: application/json

{
  "id": 123456789,
  "gateway": "VCB",
  "transactionDate": "2025-09-22 10:30:00",
  "accountNumber": "1234567890",
  "content": "TOPUP_1727001234_ABCD",
  "transferType": "bank_transfer", 
  "transferAmount": 100000,
  "referenceCode": "REF_TOPUP_1727001234_ABCD"
}
```

## Luồng xử lý chi tiết

### Bước 1: Tạo Payment Intent

1. Validate amount > 0 và <= giới hạn
2. Lấy hoặc tạo wallet cho user
3. Sinh order_code duy nhất: `TOPUP{timestamp}{random}` (format phù hợp với SePay)
4. Tạo PayPaymentIntent với:
   - purpose = 'wallet_topup'
   - status = 'requires_payment_method'
   - expires_at = now + expires_in_minutes

### Bước 2: Tạo Payment Attempt

1. Kiểm tra intent hợp lệ và chưa expired
2. Gọi SePay API tạo QR code VietQR
3. Tạo PayPaymentAttempt với thông tin QR
4. Cập nhật intent status = 'processing'

### Bước 3: Xử lý Webhook

1. Lưu thô webhook vào PaySepayWebhookEvent
2. Extract sepay_tx_id, amount, content từ payload
3. Tìm intent matching với content (order_code)
4. Validate amount khớp với intent.amount
5. Tạo PayBankTransaction để đối soát

### Bước 4: Chốt Payment

1. Tạo PayPayment với:
   - status = 'succeeded'
   - provider_payment_id = sepay_tx_id
   - liên kết với intent và user
2. Liên kết PayBankTransaction với intent và payment

### Bước 5: Ghi Ledger

1. Tính balance_before từ wallet hiện tại
2. Tính balance_after = balance_before + amount
3. Tạo PayWalletLedger entry:
   - tx_type = 'deposit'
   - is_credit = true
   - amount = payment.amount
4. Cập nhật cache số dư trong PayWallet
5. Cập nhật intent status = 'succeeded'

## Error Handling

### Validation Errors
- Amount <= 0: "Amount must be greater than 0"
- Amount > limit: "Amount exceeds maximum limit"
- Wallet suspended: "Wallet is suspended"
- Intent expired: "Intent has expired"

### Webhook Errors
- Missing sepay_tx_id: "Missing sepay transaction id in webhook"
- No matching intent: "No matching intent found for this transaction"
- Amount mismatch: "Amount mismatch"
- Duplicate processing: Idempotent với sepay_tx_id

### Payment Errors
- Insufficient balance: "Insufficient wallet balance" (cho withdraw)
- Invalid status transition: "Cannot cancel this topup request"

## Security Considerations

1. **Idempotency**: Sử dụng sepay_tx_id để tránh duplicate processing
2. **Validation**: Validate tất cả input từ webhook
3. **Authentication**: JWT required cho user endpoints  
4. **Rate Limiting**: Có thể implement rate limiting cho create topup
5. **Audit Trail**: Tất cả giao dịch được ghi log chi tiết

## Monitoring và Debug

### Logs quan trọng
- Webhook processing errors
- Amount mismatch cases
- Intent not found cases
- Balance calculation errors

### Metrics cần track
- Topup success rate
- Average processing time
- Webhook processing errors
- Amount mismatch frequency

## Testing

### Unit Tests
- WalletTopupService methods
- Model validation
- Balance calculations

### Integration Tests  
- Full topup flow
- Webhook processing
- Error scenarios

### Demo Script
Chạy demo script để test:
```bash
python demo_wallet_topup.py
python demo_wallet_topup.py --cleanup
```

## SePay Integration

### Mock Mode (Development)
Khi không có SEPAY_API_KEY, system sẽ dùng mock data:
- QR image URL từ VietQR API
- Mock account info
- Mock transaction status

### Production Mode
Cần config:
- SEPAY_API_KEY
- SEPAY_BASE_URL  
- SEPAY_ACCOUNT_NUMBER

### Webhook Configuration
SePay cần config webhook URL:
```
POST https://yourdomain.com/api/seapay/wallet/webhook/sepay
```

## Troubleshooting

### Common Issues

1. **QR code không hiển thị**
   - Check SEPAY_API_KEY config
   - Check SePay API response
   - Fallback to mock data trong dev

2. **Webhook không được xử lý**
   - Check webhook URL config ở SePay
   - Check PaySepayWebhookEvent table
   - Check process_error field

3. **Amount không khớp** 
   - Check transferAmount formatting
   - Check decimal precision
   - Check currency conversion

4. **Balance không update**
   - Check PayWalletLedger entries
   - Check balance calculation logic
   - Verify atomic transactions

## Future Enhancements

1. **Multi-currency support**
2. **Bank selection for QR**
3. **Webhook retry mechanism**  
4. **Real-time status updates via WebSocket**
5. **Advanced reconciliation rules**
6. **Automated refund processing**