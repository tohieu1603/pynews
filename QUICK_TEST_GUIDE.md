# 🚀 Test Google Login API - Quick Guide

## ⚡ Test ngay mà không cần setup Google OAuth

### 1. Khởi động server:
```bash
python manage.py runserver
```

### 2. Test API endpoints trong Postman:

#### ✅ Test 1: Health Check
- **GET** `http://localhost:8000/api/docs`
- Kết quả: Swagger UI hiển thị

#### ✅ Test 2: Get Google Auth URL (sẽ fail vì chưa setup OAuth)
- **GET** `http://localhost:8000/api/auth/google/auth-url`
- Kết quả: Trả về URL (dù credentials chưa thật)

#### ✅ Test 3: Tạo user và test traditional login
1. Tạo superuser:
```bash
python manage.py createsuperuser
```

2. Test traditional login:
- **POST** `http://localhost:8000/api/auth/login`
- Headers: `Content-Type: application/json`
- Body:
```json
{
  "email": "admin@example.com",
  "password": "your-password"
}
```

3. Copy access_token từ response

4. Test protected endpoint:
- **GET** `http://localhost:8000/api/auth/profile`
- Headers: `Authorization: Bearer your-access-token`

## 🔧 Để hoàn thành Google OAuth:

### Bước 1: Setup Google Cloud Console
1. Đi tới: https://console.cloud.google.com/
2. Tạo project → Enable APIs → Tạo OAuth credentials
3. Copy Client ID và Client Secret

### Bước 2: Cập nhật .env
```env
GOOGLE_CLIENT_ID=your-real-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-real-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/login
```

### Bước 3: Test Google OAuth flow
1. GET `/api/auth/google/auth-url` → Copy URL
2. Paste vào browser → Login Google → Copy code từ callback URL
3. POST `/api/auth/google/login` với code → Nhận JWT tokens

## 📱 Postman Collection Template

```json
{
  "info": {
    "name": "Togogo Auth API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "variable": [
    {
      "key": "base_url",
      "value": "http://localhost:8000"
    },
    {
      "key": "access_token",
      "value": ""
    }
  ],
  "item": [
    {
      "name": "Health Check",
      "request": {
        "method": "GET",
        "url": "{{base_url}}/api/docs"
      }
    },
    {
      "name": "Get Google Auth URL",
      "request": {
        "method": "GET",
        "url": "{{base_url}}/api/auth/google/auth-url"
      }
    },
    {
      "name": "Traditional Login",
      "request": {
        "method": "POST",
        "url": "{{base_url}}/api/auth/login",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"email\": \"admin@example.com\",\n  \"password\": \"your-password\"\n}"
        }
      },
      "event": [
        {
          "listen": "test",
          "script": {
            "exec": [
              "if (pm.response.code === 200) {",
              "    const responseJson = pm.response.json();",
              "    pm.environment.set('access_token', responseJson.access_token);",
              "}"
            ]
          }
        }
      ]
    },
    {
      "name": "Get Profile",
      "request": {
        "method": "GET",
        "url": "{{base_url}}/api/auth/profile",
        "header": [
          {
            "key": "Authorization",
            "value": "Bearer {{access_token}}"
          }
        ]
      }
    }
  ]
}
```

**Copy collection này vào Postman để test ngay! 🎉**
