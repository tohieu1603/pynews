
from ninja.security import HttpBearer
import jwt
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()

class JWTAuth(HttpBearer):
    def authenticate(self, request, token):
        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
            user = User.objects.get(id=payload["user_id"])
            return user
        except Exception:
            return None
import datetime as dt
from typing import Any, Dict, Tuple

import jwt
from django.conf import settings


def _now() -> dt.datetime:
    return dt.datetime.utcnow()


def create_tokens(user_id: int, email: str | None = None) -> Tuple[str, str, int, int]:
    access_ttl = int(getattr(settings, "JWT_ACCESS_TTL_MIN", 60))
    refresh_ttl_days = int(getattr(settings, "JWT_REFRESH_TTL_DAYS", 30))

    now = _now()
    access_exp = now + dt.timedelta(minutes=access_ttl)
    refresh_exp = now + dt.timedelta(days=refresh_ttl_days)

    base_claims: Dict[str, Any] = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
    }
    if email:
        base_claims["email"] = email

    access_claims = {**base_claims, "type": "access", "exp": int(access_exp.timestamp())}
    refresh_claims = {**base_claims, "type": "refresh", "exp": int(refresh_exp.timestamp())}

    secret = getattr(settings, "JWT_SECRET", settings.SECRET_KEY)
    alg = getattr(settings, "JWT_ALGORITHM", "HS256")

    access = jwt.encode(access_claims, secret, algorithm=alg)
    refresh = jwt.encode(refresh_claims, secret, algorithm=alg)
    return access, refresh, int(access_ttl * 60), int(refresh_ttl_days * 24 * 3600)


def decode_token(token: str) -> Dict[str, Any]:
    secret = getattr(settings, "JWT_SECRET", settings.SECRET_KEY)
    alg = getattr(settings, "JWT_ALGORITHM", "HS256")
    return jwt.decode(token, secret, algorithms=[alg])
