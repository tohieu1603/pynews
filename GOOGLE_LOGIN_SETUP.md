# Google OAuth Login Setup Guide

## 🚀 Hệ thống Login Google đã được tích hợp thành công!

### 📋 Chức năng đã implement:

1. **Google OAuth Login** - Đăng nhập bằng tài khoản Google
2. **Traditional Login** - Đăng nhập bằng email/password
3. **JWT Authentication** - Xác thực bằng JWT tokens
4. **User Profile Management** - Quản lý thông tin user
5. **Auto User Creation** - Tự động tạo user từ Google account

### 🔧 Cách setup Google OAuth Credentials:

1. **Truy cập Google Cloud Console:**
   - Đi tới: https://console.developers.google.com/
   - Tạo project mới hoặc chọn project hiện có

2. **Enable Google+ API:**
   - Trong sidebar, chọn "APIs & Services" > "Library"
   - Tìm "Google+ API" và enable nó
   - Cũng enable "Google OAuth2 API"

3. **Tạo OAuth Credentials:**
   - Đi tới "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Chọn "Web application"
   - Trong "Authorized redirect URIs", thêm:
     ```
     http://localhost:8000/login
     ```

4. **Cập nhật file .env:**
   ```env
   GOOGLE_CLIENT_ID=your-actual-client-id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-actual-client-secret
   GOOGLE_REDIRECT_URI=http://localhost:8000/login
   ```

### 🌐 API Endpoints đã có:

#### Authentication:
- `GET /api/auth/google/auth-url` - Lấy URL để redirect tới Google OAuth
- `POST /api/auth/google/login` - Login bằng Google OAuth code
- `POST /api/auth/login` - Login truyền thống (email/password)
- `POST /api/auth/refresh` - Refresh JWT token
- `GET /api/auth/profile` - Lấy thông tin profile (cần authentication)

### 🎯 Cách test hệ thống:

1. **Khởi động server:**
   ```bash
   python manage.py runserver
   ```

2. **Truy cập login page:**
   ```
   http://localhost:8000/login
   ```

3. **Test Google Login:**
   - Click nút "Login with Google"
   - Nếu chưa setup Google OAuth credentials, sẽ báo lỗi
   - Sau khi setup xong, sẽ redirect tới Google để login

4. **Test Traditional Login:**
   - Tạo user bằng admin panel: http://localhost:8000/admin
   - Hoặc dùng createsuperuser: `python manage.py createsuperuser`
   - Login bằng email/password trong form

5. **Test API:**
   - Swagger UI: http://localhost:8000/api/docs
   - Hoặc dùng curl/Postman để test các endpoints

### 📱 Frontend Integration:

Trong frontend (React/Vue/Angular), bạn có thể:

```javascript
// Lấy Google auth URL
const response = await fetch('/api/auth/google/auth-url');
const { auth_url } = await response.json();
window.location.href = auth_url;

// Hoặc traditional login
const loginResponse = await fetch('/api/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'password123'
  })
});

const { access_token, refresh_token, user } = await loginResponse.json();

// Sử dụng token cho các API calls
const profileResponse = await fetch('/api/auth/profile', {
  headers: { 'Authorization': `Bearer ${access_token}` }
});
```

### 🔒 Security Features:

- JWT tokens với expiration time
- Refresh token mechanism
- Password hashing với Django's built-in system
- CORS protection (có thể config thêm)
- SQL injection protection qua Django ORM

### 🗃️ Database Schema:

**CustomUser Model:**
- email (unique)
- name
- phone
- avatar_url
- is_active, is_staff
- created_at, updated_at

**SocialAccount Model:**
- provider (google/facebook)
- sub (Google user ID)
- email
- user (ForeignKey to CustomUser)

### 🚀 Next Steps:

1. Setup Google OAuth credentials
2. Test đầy đủ cả Google login và traditional login
3. Tích hợp với frontend application
4. Add thêm providers khác (Facebook, GitHub, etc.) nếu cần
5. Customize UI/UX cho login page
6. Add forgot password functionality
7. Add email verification

### 📞 Support:

Nếu có vấn đề gì, hãy check:
1. Console logs trong browser
2. Django server logs
3. Database connection
4. Google OAuth credentials setup

Hệ thống Google Login đã hoàn tất! 🎉
