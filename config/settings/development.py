from .base import *

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

# Database config cho dev (ghi đè nếu cần)
DATABASES["default"]["NAME"] = os.getenv("DB_NAME", "db_dev")
DATABASES["default"]["USER"] = os.getenv("DB_USER", "postgres")
DATABASES["default"]["PASSWORD"] = os.getenv("DB_PASSWORD", "123456789")
DATABASES["default"]["HOST"] = os.getenv("DB_HOST", "localhost")
DATABASES["default"]["PORT"] = os.getenv("DB_PORT", "5432")

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]