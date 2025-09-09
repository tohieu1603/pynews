from typing import Optional

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import JsonResponse
from ninja import Router

from .serializers import GoogleLoginIn, AuthTokensOut, UserOut, LoginResponse
from .models import SocialAccount
from core.jwt_auth import create_tokens


router = Router()


def _get_google_client_ids() -> list[str]:
    cfg = settings.GOOGLE_CLIENT_ID
    if not cfg:
        return []
    # Allow comma-separated list for multiple clients (web, ios, android)
    return [c.strip() for c in str(cfg).split(",") if c.strip()]


@router.post("google/login", response=LoginResponse)
def google_login(request, payload: GoogleLoginIn):
    # Lazy import to avoid dependency issues if not installed yet
    try:
        from google.oauth2 import id_token as g_id_token
        from google.auth.transport import requests as g_requests
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "Missing dependency 'google-auth'. Please add google-auth to requirements and install."
        ) from exc

    client_ids = _get_google_client_ids()
    if not client_ids:
        raise RuntimeError("GOOGLE_CLIENT_ID is not configured in environment/settings.")

    # Verify Google ID token signature and audience
    req = g_requests.Request()
    idinfo: Optional[dict] = None
    last_error: Optional[Exception] = None
    for aud in client_ids:
        try:
            idinfo = g_id_token.verify_oauth2_token(payload.id_token, req, aud)
            if idinfo:
                break
        except Exception as e:  # try next client id if multiple configured
            last_error = e
            continue

    if not idinfo:
        if last_error:
            raise last_error
        raise RuntimeError("Invalid Google ID token.")

    sub = idinfo.get("sub")
    email = idinfo.get("email")
    email_verified = idinfo.get("email_verified", False)
    name = idinfo.get("name")
    picture = idinfo.get("picture")

    if not sub:
        raise RuntimeError("Google token missing subject (sub).")

    User = get_user_model()

    with transaction.atomic():
        # Find existing social link
        try:
            social = SocialAccount.objects.select_related("user").get(
                provider=SocialAccount.PROVIDER_GOOGLE, sub=sub
            )
            user = social.user
        except SocialAccount.DoesNotExist:
            # No link yet; create or find by verified email
            user = None
            if email and email_verified:
                user = User.objects.filter(email__iexact=email).first()

            if not user:
                # Create a new user
                # Build a username from email or google sub
                base_username = None
                if email:
                    base_username = email.split("@")[0]
                else:
                    base_username = f"gg_{sub[:12]}"

                username = base_username
                # Ensure unique username if default User model in use
                suffix = 1
                while User.objects.filter(username=username).exists():
                    suffix += 1
                    username = f"{base_username}{suffix}"

                user = User.objects.create_user(
                    username=username,
                    email=email or None,
                    password=None,
                )
                # Optional fields if present on custom user
                if hasattr(user, "first_name") and name:
                    user.first_name = name
                if hasattr(user, "last_name") and not getattr(user, "last_name", None):
                    user.last_name = ""
                if hasattr(user, "avatar_url") and picture:
                    setattr(user, "avatar_url", picture)
                user.save()

            # Create the social link
            SocialAccount.objects.create(
                provider=SocialAccount.PROVIDER_GOOGLE, sub=sub, email=email or None, user=user
            )

    access, refresh, access_exp_s, refresh_exp_s = create_tokens(user.id, getattr(user, "email", None))

    user_out = UserOut(
        id=user.id,
        email=getattr(user, "email", None),
        username=getattr(user, "username", None),
        name=getattr(user, "first_name", None) or getattr(user, "name", None),
        avatar_url=getattr(user, "avatar_url", None),
    )

    tokens = AuthTokensOut(
        access=access, refresh=refresh, expires_in=access_exp_s, refresh_expires_in=refresh_exp_s
    )

    return LoginResponse(tokens=tokens, user=user_out)


def oauth_callback(request):
    """HTTP GET callback for Google OAuth code flow: exchanges code -> user -> JWT.

    Useful when using a browser redirect flow with GOOGLE_REDIRECT_URI pointing to /login.
    Returns JSON with tokens and user info for simplicity.
    """
    from .api import (
        get_user_info_from_google,
        create_or_get_user_from_google,
        create_jwt_token,
    )

    code = request.GET.get("code")
    if not code:
        return JsonResponse({"error": "Missing 'code' query parameter"}, status=400)

    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
    }

    try:
        token_response = requests.post(token_url, data=token_data)
        token_json = token_response.json()
        access_token = token_json.get("access_token")
        if not access_token:
            return JsonResponse(
                {"error": "Failed to get access token from Google", "details": token_json},
                status=400,
            )

        google_user_info = get_user_info_from_google(access_token)
        user = create_or_get_user_from_google(google_user_info)
        tokens = create_jwt_token(user)

        return JsonResponse(
            {
                "message": "Login successful",
                "access_token": tokens["access_token"],
                "refresh_token": tokens["refresh_token"],
                "user": {
                    "id": user.id,
                    "email": getattr(user, "email", None),
                    "username": getattr(user, "username", None),
                    "first_name": getattr(user, "first_name", None),
                    "last_name": getattr(user, "last_name", None),
                },
            }
        )
    except Exception as e:
        return JsonResponse({"error": f"OAuth callback failed: {e}"}, status=400)
