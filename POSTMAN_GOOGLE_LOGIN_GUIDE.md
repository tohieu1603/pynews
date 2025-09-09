# 🚀 Hướng dẫn Test Google Login với Postman

## 📋 Tổng quan hệ thống

Hệ thống Google Login đã được tích hợp với Django Ninja API và hỗ trợ:
- ✅ Google OAuth 2.0 Login
- ✅ Traditional Email/Password Login  
- ✅ JWT Token Authentication
- ✅ User Profile Management

## 🔧 Chuẩn bị môi trường

### 1. Khởi động server
```bash
cd "C:\Users\ADMIN\TogogoAnalysiss\TogogoAnalysis"
python manage.py runserver
```

### 2. Kiểm tra server hoạt động
- URL: `http://localhost:8000/api/docs`
- Kết quả: Swagger UI hiển thị các API endpoints

## 📊 API Endpoints có sẵn

### 🔐 Authentication APIs

#### 1. GET `/api/auth/google/auth-url`
**Lấy Google OAuth URL để redirect**
- **Method:** `GET`
- **URL:** `http://localhost:8000/api/auth/google/auth-url`
- **Headers:** Không cần
- **Response:**
```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/auth?response_type=code&client_id=..."
}
```

#### 2. POST `/api/auth/google/login`
**Login với Google OAuth code**
- **Method:** `POST`
- **URL:** `http://localhost:8000/api/auth/google/login`
- **Headers:** `Content-Type: application/json`
- **Body:**
```json
{
  "code": "4/0AanQ5DhzQ8X..."
}
```
- **Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "id": 1,
    "email": "user@gmail.com",
    "username": "user@gmail.com",
    "first_name": "John Doe",
    "last_name": ""
  }
}
```

#### 3. POST `/api/auth/login`
**Traditional Login**
- **Method:** `POST`
- **URL:** `http://localhost:8000/api/auth/login`
- **Headers:** `Content-Type: application/json`
- **Body:**
```json
{
  "email": "admin@example.com",
  "password": "your-password"
}
```

#### 4. GET `/api/auth/profile`
**Lấy thông tin profile (cần authentication)**
- **Method:** `GET`
- **URL:** `http://localhost:8000/api/auth/profile`
- **Headers:** `Authorization: Bearer your-access-token`
- **Response:**
```json
{
  "id": 1,
  "email": "user@gmail.com",
  "username": "user@gmail.com",
  "first_name": "John Doe",
  "last_name": "",
  "date_joined": "2025-09-05T10:30:00Z"
}
```

## 🧪 Hướng dẫn Test từng bước

### Step 1: Setup Google OAuth Credentials

1. **Tạo Google OAuth App:**
   - Truy cập: https://console.developers.google.com/
   - Tạo project mới hoặc chọn project có sẵn
   - Enable "Google+ API" và "OAuth2 API"
   - Tạo "OAuth 2.0 Client ID"
   - Chọn "Web application"
   - Thêm Authorized redirect URIs: `http://localhost:8000/login`

2. **Cập nhật file .env:**
```env
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/login
```

### Step 2: Test trong Postman

#### 🔍 Test 1: Health Check
1. Tạo request mới trong Postman
2. **GET** `http://localhost:8000/api/docs`
3. Send → Kiểm tra có trả về Swagger UI

#### 🔍 Test 2: Lấy Google Auth URL
1. **GET** `http://localhost:8000/api/auth/google/auth-url`
2. Send → Copy `auth_url` từ response
3. Paste URL vào browser để test OAuth flow

#### 🔍 Test 3: Test Google Login Flow (Manual)
1. Paste `auth_url` vào browser
2. Login với Google account
3. Sau khi redirect, copy `code` parameter từ URL
4. Trong Postman:
   - **POST** `http://localhost:8000/api/auth/google/login`
   - Body: `{"code": "copied-code-here"}`
   - Send → Lưu `access_token` từ response

#### 🔍 Test 4: Test Protected Endpoint
1. **GET** `http://localhost:8000/api/auth/profile`
2. Headers: `Authorization: Bearer your-access-token`
3. Send → Kiểm tra thông tin user

#### 🔍 Test 5: Traditional Login (nếu có user)
1. Tạo superuser: `python manage.py createsuperuser`
2. **POST** `http://localhost:8000/api/auth/login`
3. Body: `{"email": "admin@example.com", "password": "password"}`

## 📱 Postman Collection Template

### Environment Variables
```
base_url = http://localhost:8000
google_auth_code = (manual input)
access_token = (auto set từ login response)
refresh_token = (auto set từ login response)
```

### Collection Structure
```
📁 Togogo Auth API
├── 🔍 Health Check [GET] {{base_url}}/api/docs
├── 🔐 Get Google Auth URL [GET] {{base_url}}/api/auth/google/auth-url
├── 🔐 Google Login [POST] {{base_url}}/api/auth/google/login
├── 🔐 Traditional Login [POST] {{base_url}}/api/auth/login
└── 👤 Get Profile [GET] {{base_url}}/api/auth/profile
```

## 🔧 Scripts tự động trong Postman

### Pre-request Script cho Google Login:
```javascript
// Có thể thêm validation cho code
if (!pm.environment.get("google_auth_code")) {
    console.log("Cần set google_auth_code từ OAuth flow");
}
```

### Test Script cho Login Response:
```javascript
// Auto save tokens
if (pm.response.code === 200) {
    const responseJson = pm.response.json();
    pm.environment.set("access_token", responseJson.access_token);
    pm.environment.set("refresh_token", responseJson.refresh_token);
    console.log("Tokens saved successfully!");
}
```

## ⚡ Quick Test với cURL

```bash
# Health check
curl http://localhost:8000/api/docs

# Get Google auth URL
curl http://localhost:8000/api/auth/google/auth-url

# Google login (thay YOUR_GOOGLE_CODE)
curl -X POST http://localhost:8000/api/auth/google/login \
  -H "Content-Type: application/json" \
  -d '{"code":"YOUR_GOOGLE_CODE"}'

# Get profile (thay YOUR_ACCESS_TOKEN)
curl http://localhost:8000/api/auth/profile \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## 🐛 Troubleshooting

### Lỗi thường gặp:

1. **"No module named 'authlib'"**
   ```bash
   pip install authlib PyJWT requests
   ```

2. **"Invalid Google OAuth credentials"**
   - Kiểm tra GOOGLE_CLIENT_ID và GOOGLE_CLIENT_SECRET trong .env
   - Đảm bảo redirect URI match chính xác

3. **"JWT decode error"**
   - Token có thể đã hết hạn
   - Kiểm tra JWT_SECRET trong settings

4. **"User not authenticated"**
   - Kiểm tra Authorization header format: `Bearer token`
   - Token phải valid và chưa expire

## 📈 Test Flow hoàn chỉnh

1. ✅ Start server → `python manage.py runserver`
2. ✅ Health check → GET `/api/docs`
3. ✅ Get auth URL → GET `/api/auth/google/auth-url`
4. ✅ Manual OAuth → Paste URL → Login → Copy code
5. ✅ Google login → POST `/api/auth/google/login`
6. ✅ Save tokens → Auto từ response
7. ✅ Test profile → GET `/api/auth/profile`

## 🎯 Kết quả mong đợi

- ✅ Server chạy thành công trên port 8000
- ✅ Swagger UI hiển thị đầy đủ endpoints  
- ✅ Google OAuth flow hoạt động
- ✅ JWT tokens được tạo và validate
- ✅ User profile accessible với valid token

**🎉 Hệ thống Google Login đã sẵn sàng để test!**

## 📋 Chuẩn bị

### 1. Đảm bảo server đang chạy:
```bash
python manage.py runserver
```
Server sẽ chạy tại: `http://localhost:8000`

### 2. Kiểm tra API docs:
Mở browser: `http://localhost:8000/api/docs` để xem Swagger UI

## 🧪 Test APIs với Postman

### 📖 Collection Setup

Tạo Postman Collection với tên **"Togogo Google Login API"**

#### Environment Variables:
```
base_url: http://localhost:8000
google_auth_code: (sẽ được set manual sau khi có từ Google OAuth)
access_token: (sẽ được set từ response)
refresh_token: (sẽ được set từ response)
admin_email: admin@example.com
admin_password: admin123
```

---

## 🔗 API Endpoints để test

### 1. 🏥 Health Check
**GET** `{{base_url}}/api/docs`

- **Method:** GET
- **URL:** `{{base_url}}/api/docs`
- **Expected Response:** HTML page với Swagger UI

---

### 2. 🔗 Get Google Auth URL
**GET** `{{base_url}}/api/auth/google/auth-url`

- **Method:** GET
- **URL:** `{{base_url}}/api/auth/google/auth-url`
- **Headers:** None
- **Expected Response:**
```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/auth?response_type=code&client_id=..."
}
```

**📝 Test Steps:**
1. Send request
2. Copy `auth_url` từ response
3. Paste vào browser để test Google OAuth flow

---

### 3. 🔐 Google OAuth Login
**POST** `{{base_url}}/api/auth/google/login`

- **Method:** POST
- **URL:** `{{base_url}}/api/auth/google/login`
- **Headers:**
  ```
  Content-Type: application/json
  ```
- **Body (raw JSON):**
```json
{
  "code": "{{google_auth_code}}"
}
```

- **Expected Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "id": 1,
    "email": "user@gmail.com",
    "username": "user@gmail.com",
    "first_name": "User Name",
    "last_name": ""
  }
}
```

**📝 Test Steps:**
1. Trước tiên, gọi API "Get Google Auth URL"
2. Copy `auth_url` và mở trong browser
3. Login với Google account
4. Sau khi redirect, copy `code` parameter từ URL
5. Paste code vào body request này
6. Gửi request
7. Save `access_token` và `refresh_token` vào environment variables

---

### 4. 👤 Traditional Login
**POST** `{{base_url}}/api/auth/login`

- **Method:** POST
- **URL:** `{{base_url}}/api/auth/login`
- **Headers:**
  ```
  Content-Type: application/json
  ```
- **Body (raw JSON):**
```json
{
  "email": "{{admin_email}}",
  "password": "{{admin_password}}"
}
```

**📝 Test Steps:**
1. Trước tiên cần tạo user: `python manage.py createsuperuser`
2. Gửi request với email/password
3. Save tokens từ response

---

### 5. 👨‍💼 Get User Profile
**GET** `{{base_url}}/api/auth/profile`

- **Method:** GET
- **URL:** `{{base_url}}/api/auth/profile`
- **Headers:**
  ```
  Authorization: Bearer {{access_token}}
  ```

- **Expected Response:**
```json
{
  "id": 1,
  "email": "user@gmail.com",
  "username": "user@gmail.com",
  "first_name": "User Name",
  "last_name": "",
  "date_joined": "2024-01-01T00:00:00Z"
}
```

**📝 Test Steps:**
1. Đảm bảo đã có access_token từ login
2. Add Bearer token vào Authorization header
3. Gửi request

---

## 🔧 Setup Google OAuth Credentials

### Bước 1: Tạo Google Cloud Project
1. Đi tới: https://console.developers.google.com/
2. Tạo project mới hoặc chọn project hiện có
3. Enable APIs cần thiết

### Bước 2: Enable APIs
1. Vào "APIs & Services" > "Library"
2. Tìm và enable:
   - Google+ API
   - Google OAuth2 API
   - Google People API

### Bước 3: Tạo OAuth Credentials
1. Vào "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. Chọn "Web application"
4. Thêm Authorized redirect URIs:
   ```
   http://localhost:8000/login
   http://localhost:8000/api/auth/google/callback
   ```

### Bước 4: Cập nhật .env file
```env
GOOGLE_CLIENT_ID=your-actual-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-actual-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/login
```

---

## 🧪 Complete Test Flow

### Scenario 1: Test Google Login
```
1. GET /api/auth/google/auth-url
   ↓ Get auth_url
   
2. Open auth_url in browser
   ↓ Login with Google
   
3. Copy 'code' from redirect URL
   ↓ Use code in next request
   
4. POST /api/auth/google/login
   ↓ Get access_token
   
5. GET /api/auth/profile
   ↓ Test protected endpoint
```

### Scenario 2: Test Traditional Login
```
1. Create superuser in Django admin
   
2. POST /api/auth/login
   ↓ Get access_token
   
3. GET /api/auth/profile
   ↓ Test protected endpoint
```

---

## 🐛 Troubleshooting

### Common Errors:

#### 1. "No module named 'authlib'"
**Solution:**
```bash
pip install authlib PyJWT
```

#### 2. "Invalid Google OAuth credentials"
**Check:**
- GOOGLE_CLIENT_ID trong .env
- GOOGLE_CLIENT_SECRET trong .env  
- Redirect URI match exactly

#### 3. "JWT decode error" 
**Check:**
- JWT_SECRET trong .env
- Token có thể hết hạn (60 minutes default)

#### 4. Server không start
**Check:**
- Virtual environment activated
- All packages installed
- No syntax errors trong code

---

## 📱 Quick Test với cURL

### Get Google Auth URL:
```bash
curl -X GET "http://localhost:8000/api/auth/google/auth-url"
```

### Test Profile endpoint:
```bash
curl -X GET "http://localhost:8000/api/auth/profile" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Traditional Login:
```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "admin123"
  }'
```

---

## ✅ Success Indicators

1. **✅ Server starts without errors**
2. **✅ Swagger UI accessible at /api/docs**
3. **✅ Google auth URL generates successfully**
4. **✅ Google OAuth flow completes**
5. **✅ JWT tokens returned**
6. **✅ Protected endpoints work with Bearer token**

Hệ thống Google Login sẵn sàng để test! 🎉
