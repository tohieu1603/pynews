# 🔄 Hướng Dẫn Tự Động Gia Hạn License

## 📋 Tổng quan

Khi mua license cho Symbol, hệ thống tự động tạo subscription (mặc định: **Tắt**). User có thể bật/tắt auto-renew bất cứ lúc nào.

---

## 🚀 Cách Sử Dụng

### 1️⃣ Mua License (Subscription tự động được tạo)

```bash
POST /api/sepay/symbol/orders/
Authorization: Bearer {jwt_token}
```

```json
{
  "items": [{
    "symbol_id": 1,
    "price": 200000,
    "license_days": 30
  }],
  "payment_method": "wallet"
}
```

**Kết quả:**
- ✅ License được kích hoạt
- ✅ Subscription được tạo (status: `paused`, tức là **TẮT**)
- ✅ Lưu giá & thời gian để sử dụng khi bật auto-renew

---

### 2️⃣ Xem Danh Sách License & Subscription

```bash
GET /api/sepay/symbol/licenses?page=1&limit=20
Authorization: Bearer {jwt_token}
```

**Response:**

```json
{
  "results": [
    {
      "license_id": "abc-123",
      "symbol_id": 1,
      "symbol_name": "AAPL",
      "status": "active",
      "start_at": "2025-10-07T00:00:00Z",
      "end_at": "2025-11-06T00:00:00Z",
      "is_lifetime": false,
      "is_active": true,
      "purchase_price": 200000,
      "license_days": 30,

      "subscription": {
        "subscription_id": "def-456",
        "status": "paused",           // ← TẮT auto-renew
        "is_active": false,
        "price": 200000,              // ← Giá khi gia hạn
        "cycle_days": 30,             // ← Chu kỳ gia hạn (30 ngày)
        "next_billing_at": null       // ← null vì đang tắt
      }
    }
  ],
  "total": 1,
  "page": 1,
  "limit": 20
}
```

---

### 3️⃣ BẬT Auto-Renew (Resume Subscription)

```bash
POST /api/settings/symbol/subscriptions/{subscription_id}/resume
Authorization: Bearer {jwt_token}
```

**Kết quả:**
- ✅ Status chuyển sang `active`
- ✅ `next_billing_at` được set = `license.end_at - 12 giờ`
- ✅ Cronjob sẽ tự động gia hạn trước 12 giờ khi hết hạn

---

### 4️⃣ TẮT Auto-Renew (Pause Subscription)

```bash
POST /api/settings/symbol/subscriptions/{subscription_id}/pause
Authorization: Bearer {jwt_token}
```

**Kết quả:**
- ✅ Status chuyển sang `paused`
- ✅ `next_billing_at` = `null`
- ✅ License hiện tại vẫn valid đến hết hạn
- ✅ Không tự động gia hạn nữa

---

### 5️⃣ HỦY Auto-Renew (Cancel Subscription)

```bash
POST /api/settings/symbol/subscriptions/{subscription_id}/cancel
Authorization: Bearer {jwt_token}
```

**Kết quả:**
- ✅ Status chuyển sang `cancelled` (vĩnh viễn)
- ✅ Không thể resume lại
- ✅ Phải mua license mới nếu muốn bật lại auto-renew

---

## ⚙️ Setup Cronjob (Admin)

Để auto-renew hoạt động, cần setup cronjob chạy định kỳ:

### Option 1: Cronjob (Khuyến nghị)

```bash
# Chạy mỗi 5 phút
*/5 * * * * cd /path/to/project && python manage.py run_autorenew >> /var/log/autorenew.log 2>&1
```

### Option 2: Manual Test

```bash
python manage.py run_autorenew --verbose
```

**Output:**
```
✓ Processed: 10 | Success: 8 | Failed: 1 | Skipped: 1
```

---

## 🔄 Luồng Hoạt Động

```
1. User MUA license (30 ngày, 200k)
   → Subscription tạo (PAUSED, price=200k, cycle=30d)

2. User BẬT auto-renew
   → Status = ACTIVE
   → next_billing_at = license.end_at - 12h

3. Cronjob chạy mỗi 5 phút
   → Tìm subscriptions có next_billing_at <= now
   → Check ví có đủ tiền không?

4a. Đủ tiền:
   → Tạo order mới (200k, 30 ngày)
   → Trừ ví tự động
   → Extend license.end_at thêm 30 ngày
   → Set next_billing_at = new_end_at - 12h

4b. Thiếu tiền:
   → Cancel subscription ngay
   → User phải nạp tiền + bật lại manually
```

---

## 💡 Lưu Ý

### ✅ Ưu điểm
- Không cần nhập thông tin thanh toán lại
- Tự động gia hạn trước 12h (không bị gián đoạn)
- Bật/tắt bất cứ lúc nào
- Giữ nguyên giá & thời gian lúc mua đầu tiên

### ⚠️ Điều kiện
- **Chỉ hỗ trợ thanh toán bằng ví** (wallet)
- Ví phải có đủ tiền khi đến hạn
- Thiếu tiền → Auto-cancel (không retry)

### 🔒 Bảo mật
- Subscription chỉ active với license đang có hiệu lực
- Không thể bật auto-renew cho license đã hết hạn
- Mỗi symbol chỉ có 1 subscription

---

## 📊 Monitoring (Admin)

### Check subscriptions sắp đến hạn:

```sql
SELECT user_id, symbol_id, next_billing_at, price
FROM symbol_autorenew_subscriptions
WHERE status = 'active'
  AND next_billing_at <= NOW() + INTERVAL '1 hour';
```

### Check failed attempts:

```sql
SELECT s.user_id, s.symbol_id, a.fail_reason, a.ran_at
FROM symbol_autorenew_attempts a
JOIN symbol_autorenew_subscriptions s ON a.subscription_id = s.subscription_id
WHERE a.status = 'failed'
  AND a.ran_at >= NOW() - INTERVAL '24 hours'
ORDER BY a.ran_at DESC;
```

---

## 🐛 Troubleshooting

### Subscription không gia hạn?

1. **Check subscription status:**
   ```bash
   GET /api/settings/symbol/subscriptions
   ```
   → Status phải là `active`

2. **Check số dư ví:**
   ```bash
   GET /api/sepay/wallet/balance
   ```
   → Balance >= subscription.price

3. **Check cronjob:**
   ```bash
   python manage.py run_autorenew --verbose
   ```

4. **Check logs:**
   ```bash
   tail -f /var/log/autorenew.log
   ```

---

## 📖 API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/sepay/symbol/licenses` | GET | Xem licenses + subscription info |
| `/api/settings/symbol/subscriptions` | GET | Xem tất cả subscriptions |
| `/api/settings/symbol/subscriptions/{id}/resume` | POST | Bật auto-renew |
| `/api/settings/symbol/subscriptions/{id}/pause` | POST | Tắt auto-renew |
| `/api/settings/symbol/subscriptions/{id}/cancel` | POST | Hủy vĩnh viễn |
| `/api/settings/symbol/subscriptions/{id}/attempts` | GET | Xem lịch sử gia hạn |

---

**Version:** 1.0.0
**Last Updated:** 2025-10-07
