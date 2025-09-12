# Calculate API Import Documentation

## Overview
API endpoints để import dữ liệu tài chính từ VNStock vào Django models, sử dụng Django Ninja framework theo cấu trúc như Stock module.

## Base URL
```
http://localhost:8000/api/calculate/
```

## API Documentation
Xem chi tiết tại: `http://localhost:8000/api/docs` (Django Ninja auto-generated docs)

## Endpoints

### 1. Import Balance Sheet cho 1 Symbol
**POST** `/api/calculate/import/balance-sheet/symbol`

Import chỉ balance sheet data cho 1 mã cổ phiếu.

**Request Body:**
```json
{
    "symbol": "VIC",
    "force_update": false
}
```

**Response (Success):**
```json
{
    "symbol": "VIC",
    "success": true,
    "balance_sheets": 5,
    "income_statements": 0,
    "cash_flows": 0,
    "ratios": 0,
    "errors": [],
    "processing_time": 2.34
}
```

### 2. Import Tất cả Financial Data cho 1 Symbol
**POST** `/api/calculate/import/all/symbol`

Import tất cả dữ liệu tài chính (balance sheet, income statement, cash flow, ratios).

**Request Body:**
```json
{
    "symbol": "VCB",
    "force_update": true
}
```

**Response (Success):**
```json
{
    "symbol": "VCB",
    "success": true,
    "balance_sheets": 5,
    "income_statements": 5,
    "cash_flows": 5,
    "ratios": 5,
    "errors": [],
    "processing_time": 4.67
}
```

### 3. Import từ Exchange
**POST** `/api/calculate/import/exchange`

Import financial data cho tất cả symbols trong sàn giao dịch.

**Request Body:**
```json
{
    "exchange": "HSX",
    "limit": 10,
    "sleep_seconds": 1.5
}
```

**Parameters:**
- `exchange`: HSX, HNX, hoặc UPCOM
- `limit`: Giới hạn số symbols để test (optional, max 1000)
- `sleep_seconds`: Thời gian nghỉ giữa các requests (0.1-10.0)

**Response (Success):**
```json
{
    "exchange": "HSX",
    "total_symbols": 10,
    "successful_imports": 8,
    "failed_imports": 2,
    "total_balance_sheets": 40,
    "total_income_statements": 35,
    "total_cash_flows": 30,
    "total_ratios": 38,
    "processing_time": 25.43,
    "results": [
        {
            "symbol": "VIC",
            "success": true,
            "balance_sheets": 5,
            "income_statements": 4,
            "cash_flows": 4,
            "ratios": 5,
            "errors": []
        }
    ]
}
```

### 4. Health Check
**GET** `/api/calculate/status`

Kiểm tra status của service.

**Response:**
```json
{
    "service": "Calculate Import API",
    "status": "healthy",
    "version": "1.0.0",
    "endpoints": [
        "POST /api/calculate/import/balance-sheet/symbol",
        "POST /api/calculate/import/all/symbol",
        "POST /api/calculate/import/exchange",
        "GET /api/calculate/status"
    ]
}
```

## Error Responses

**400 Bad Request:**
```json
{
    "detail": "Symbol 'INVALID' not found in database"
}
```

**500 Internal Server Error:**
```json
{
    "detail": "Error importing balance sheet for VIC: Connection timeout"
}
```

## Usage Examples

### cURL Examples

1. **Import balance sheet:**
```bash
curl -X POST http://localhost:8000/api/calculate/import/balance-sheet/symbol \
  -H "Content-Type: application/json" \
  -d '{"symbol": "VIC"}'
```

2. **Import all financials:**
```bash
curl -X POST http://localhost:8000/api/calculate/import/all/symbol \
  -H "Content-Type: application/json" \
  -d '{"symbol": "VCB", "force_update": true}'
```

3. **Import from exchange (limited):**
```bash
curl -X POST http://localhost:8000/api/calculate/import/exchange \
  -H "Content-Type: application/json" \
  -d '{"exchange": "HSX", "limit": 5, "sleep_seconds": 2.0}'
```

4. **Check status:**
```bash
curl http://localhost:8000/api/calculate/status
```

### Python Examples

```python
import requests

base_url = "http://localhost:8000/api/calculate"

# Import balance sheet for VIC
response = requests.post(
    f"{base_url}/import/balance-sheet/symbol",
    json={"symbol": "VIC"}
)
print(response.json())

# Import all financials with force update
response = requests.post(
    f"{base_url}/import/all/symbol",
    json={"symbol": "VCB", "force_update": True}
)
print(response.json())

# Import limited symbols from HSX
response = requests.post(
    f"{base_url}/import/exchange",
    json={
        "exchange": "HSX", 
        "limit": 10, 
        "sleep_seconds": 1.5
    }
)
print(response.json())
```

### JavaScript/Frontend Examples

```javascript
const baseUrl = 'http://localhost:8000/api/calculate';

// Import balance sheet
const importBalanceSheet = async (symbol) => {
    const response = await fetch(`${baseUrl}/import/balance-sheet/symbol`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ symbol })
    });
    return response.json();
};

// Import all financials
const importAllFinancials = async (symbol, forceUpdate = false) => {
    const response = await fetch(`${baseUrl}/import/all/symbol`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
            symbol, 
            force_update: forceUpdate 
        })
    });
    return response.json();
};

// Usage
importBalanceSheet('VIC').then(result => console.log(result));
importAllFinancials('VCB', true).then(result => console.log(result));
```

## API Schema Validation

Django Ninja tự động validate input/output schemas:

### Input Schemas:
- **ImportSymbolSchema**: `symbol` (required), `force_update` (optional)
- **ImportExchangeSchema**: `exchange`, `limit`, `sleep_seconds`

### Output Schemas:
- **ImportResultSchema**: Kết quả import cho 1 symbol
- **ImportSummarySchema**: Tổng kết import exchange
- **StatusSchema**: Thông tin service status

## Performance Notes

- Sử dụng `sleep_seconds` để tránh rate limiting từ VNStock API
- `limit` parameter để test với số lượng nhỏ trước khi import full exchange
- Import exchange có thể mất nhiều thời gian (hàng trăm symbols)
- Monitoring qua `processing_time` trong response

## Architecture

```
apps/calculate/
├── routers/
│   ├── __init__.py
│   └── calculate.py          # Ninja API routes
├── services/
│   ├── __init__.py
│   └── financial_service.py  # Business logic service
├── constants.py              # VNStock field constants
├── models.py                 # Django models
└── repositories.py           # Database operations

api/
└── router.py                 # Main API router (includes calculate router)
```

## Integration

API này được tích hợp vào main API router tại `/api/calculate/` và có thể access qua:
- Interactive docs: `http://localhost:8000/api/docs`
- OpenAPI schema: `http://localhost:8000/api/openapi.json`