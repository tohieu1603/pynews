# Togogo Analysis - Stock Analysis API

Dự án phân tích chứng khoán sử dụng Django + Django Ninja với cơ sở dữ liệu PostgreSQL.

## Cấu trúc dự án

```
TogogoAnalysis/
├── api/                        # API configuration
│   ├── __init__.py
│   ├── dependencies.py
│   ├── exceptions.py
│   ├── main.py                 # Main API instance
│   ├── middleware.py
│   └── router.py
├── apps/                       # Django apps
│   └── stock/                  # Stock analysis app
│       ├── __init__.py
│       ├── api.py              # Stock API endpoints
│       ├── apps.py             # App configuration
│       ├── filters.py
│       ├── models.py           # Database models
│       ├── schemas.py          # Pydantic schemas
│       ├── services.py         # Business logic
│       ├── utils.py
│       ├── migrations/         # Database migrations
│       └── tests/              # Unit tests
├── config/                     # Django configuration
│   ├── __init__.py
│   ├── asgi.py                 # ASGI configuration
│   ├── urls.py                 # URL routing
│   ├── wsgi.py                 # WSGI configuration
│   └── settings/
│       ├── __init__.py
│       ├── base.py             # Base settings
│       ├── development.py      # Development settings
│       └── production.py       # Production settings
├── core/                       # Core utilities
├── database/                   # Database utilities
├── manage.py                   # Django management script
├── requirement.txt             # Python dependencies
└── .env                        # Environment variables
```

## Yêu cầu hệ thống

- Python 3.8+
- PostgreSQL 12+
- pip

## Cài đặt và cấu hình

### 1. Clone repository

```bash
git clone <repository-url>
cd TogogoAnalysis
```

### 2. Tạo virtual environment (khuyến nghị)

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate
```

### 3. Cài đặt dependencies

```bash
pip install -r requirement.txt
```

### 4. Cấu hình PostgreSQL

#### Cài đặt PostgreSQL:
- Windows: Tải từ https://www.postgresql.org/download/windows/
- Mac: `brew install postgresql`
- Ubuntu: `sudo apt-get install postgresql postgresql-contrib`

#### Tạo database:
```sql
-- Kết nối vào PostgreSQL với user postgres
psql -U postgres

-- Tạo database
CREATE DATABASE hieu;
-- hoặc thay đổi tên database trong file .env

-- Tạo user (tùy chọn)
CREATE USER your_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE hieu TO your_user;
```

### 5. Cấu hình environment variables

Tạo file `.env` trong thư mục root:

```env
DJANGO_SETTINGS_MODULE=config.settings.development

# Database Configuration
DB_NAME=hieu
DB_USER=postgres
DB_PASSWORD=123456789
DB_HOST=localhost
DB_PORT=5432

# Security (cho production)
SECRET_KEY=your-secret-key-here
DEBUG=True
```

**Lưu ý:** Thay đổi các thông số database cho phù hợp với cấu hình PostgreSQL của bạn.

## Database Migration

### 1. Tạo migrations

```bash
# Tạo migrations cho tất cả apps
python manage.py makemigrations

# Tạo migrations cho app cụ thể
python manage.py makemigrations stock
```

### 2. Áp dụng migrations

```bash
# Áp dụng tất cả migrations
python manage.py migrate

# Kiểm tra trạng thái migrations
python manage.py showmigrations
```

### 3. Kiểm tra database connection

```bash
# Kiểm tra cấu hình database
python manage.py check --database default

# Kết nối trực tiếp đến database
python manage.py dbshell
```

## Chạy server

### Development server

```bash
# Chạy development server
python manage.py runserver

# Chạy trên port khác
python manage.py runserver 8080

# Chạy trên IP khác
python manage.py runserver 0.0.0.0:8000
```

Server sẽ chạy tại: http://127.0.0.1:8000/

### API Documentation

- Swagger UI: http://127.0.0.1:8000/api/docs
- OpenAPI Schema: http://127.0.0.1:8000/api/openapi.json

## API Endpoints

### Stock API

- `POST /api/stocks/industries` - Lấy danh sách ngành
- `POST /api/stocks/symbols` - Lấy danh sách mã chứng khoán
- `GET /api/stocks/companies/` - Lấy danh sách công ty
- `POST /api/stocks/companies/` - Tạo công ty mới

## Quản lý dữ liệu

### Tạo superuser

```bash
python manage.py createsuperuser
```

### Django Admin

Truy cập Django Admin tại: http://127.0.0.1:8000/admin/

### Import dữ liệu mẫu

```bash
# Load fixtures (nếu có)
python manage.py loaddata database/fixtures/initial_data.json
```

## Testing

```bash
# Chạy tất cả tests
python manage.py test

# Chạy tests cho app cụ thể
python manage.py test apps.stock

# Chạy với coverage
pip install coverage
coverage run --source='.' manage.py test
coverage report
coverage html
```

## Troubleshooting

### Lỗi kết nối PostgreSQL

1. **Kiểm tra PostgreSQL service đang chạy:**
   ```bash
   # Windows
   net start postgresql-x64-14
   
   # Linux
   sudo systemctl start postgresql
   sudo systemctl status postgresql
   ```

2. **Kiểm tra thông tin kết nối trong .env**

3. **Test kết nối manually:**
   ```bash
   psql -h localhost -U postgres -d hieu
   ```

### Lỗi migrations

1. **Reset migrations (cẩn thận - sẽ mất dữ liệu):**
   ```bash
   # Xóa migration files
   find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
   find . -path "*/migrations/*.pyc" -delete
   
   # Tạo lại migrations
   python manage.py makemigrations
   python manage.py migrate
   ```

2. **Fake migrations:**
   ```bash
   python manage.py migrate --fake-initial
   ```

### Lỗi import modules

1. **Kiểm tra PYTHONPATH:**
   ```bash
   export PYTHONPATH="${PYTHONPATH}:$(pwd)"
   ```

2. **Kiểm tra DJANGO_SETTINGS_MODULE:**
   ```bash
   export DJANGO_SETTINGS_MODULE=config.settings.development
   ```

## Production Deployment

### Environment setup

```env
DJANGO_SETTINGS_MODULE=config.settings.production
DEBUG=False
SECRET_KEY=your-very-secure-secret-key
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database
DB_NAME=production_db_name
DB_USER=production_user
DB_PASSWORD=secure_password
DB_HOST=your-db-host
DB_PORT=5432
```

### Collect static files

```bash
python manage.py collectstatic
```

### Use production WSGI/ASGI server

```bash
# Gunicorn example
pip install gunicorn
gunicorn config.wsgi:application

# Uvicorn for ASGI
pip install uvicorn
uvicorn config.asgi:application
```

## Đóng góp

1. Fork repository
2. Tạo feature branch: `git checkout -b feature/new-feature`
3. Commit changes: `git commit -am 'Add new feature'`
4. Push branch: `git push origin feature/new-feature`
5. Tạo Pull Request

## License

[Thêm thông tin license nếu cần]

## Support

Nếu có vấn đề, vui lòng tạo issue trên GitHub hoặc liên hệ team phát triển.
