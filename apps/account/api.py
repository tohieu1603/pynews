from ninja import Router
from ninja.responses import Response
from pydantic import BaseModel
from django.contrib.auth import authenticate, get_user_model
from django.conf import settings
from urllib.parse import urlencode
import datetime
import requests
from typing import Optional, List
from .models import SocialAccount
import jwt

User = get_user_model()
router = Router()

# Pydantic schemas
class LoginRequest(BaseModel):
    email: str
    password: str

class GoogleLoginRequest(BaseModel):
    code: str

class GoogleIdTokenRequest(BaseModel):
    id_token: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: dict

class MessageResponse(BaseModel):
    message: str

class GoogleAuthUrlResponse(BaseModel):
    auth_url: str

# Helper functions
def create_jwt_token(user) -> dict:
    """Create JWT access and refresh tokens for a user"""
    from datetime import datetime, timedelta, timezone
    
    access_payload = {
        'user_id': user.id,
        'email': user.email,
        'exp': datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_TTL_MIN),
        'iat': datetime.now(timezone.utc),
        'type': 'access'
    }
    
    refresh_payload = {
        'user_id': user.id,
        'exp': datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TTL_DAYS),
        'iat': datetime.now(timezone.utc),
        'type': 'refresh'
    }
    
    access_token = jwt.encode(access_payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    refresh_token = jwt.encode(refresh_payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    
    return {
        'access_token': access_token,
        'refresh_token': refresh_token
    }

def get_user_info_from_google(access_token: str) -> dict:
    """Get user information from Google using access token"""
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get('https://www.googleapis.com/oauth2/v2/userinfo', headers=headers)
    
    if response.status_code != 200:
        raise ValueError("Failed to get user info from Google")
    
    return response.json()

def create_or_get_user_from_google(google_user_info: dict):
    """Create or get user from Google user information"""
    email = google_user_info.get('email')
    name = google_user_info.get('name', '')
    given_name = google_user_info.get('given_name')
    family_name = google_user_info.get('family_name')
    sub = google_user_info.get('sub') or google_user_info.get('id')
    
    if sub:
        linked = SocialAccount.objects.select_related('user').filter(
            provider=SocialAccount.PROVIDER_GOOGLE, sub=str(sub)
        ).first()
        if linked:
            user = linked.user
        else:
            user = User.objects.filter(email=email).first()
            if not user:
                user = User.objects.create_user(
                    username=email or f"gg_{sub}",
                    email=email,
                )
            SocialAccount.objects.get_or_create(
                provider=SocialAccount.PROVIDER_GOOGLE,
                sub=str(sub),
                defaults={"email": email or None, "user": user},
            )
    else:
        user = User.objects.filter(email=email).first()
        if not user:
            user = User.objects.create_user(
                username=email,
                email=email,
            )
    
    changed = False
    if hasattr(user, 'first_name') and (given_name or name) and not user.first_name:
        user.first_name = given_name or name
        changed = True
    if hasattr(user, 'last_name') and family_name and not user.last_name:
        user.last_name = family_name
        changed = True
    if changed:
        user.save()
    return user

@router.get("/google/auth-url", response=GoogleAuthUrlResponse)
def get_google_auth_url(request):
    """Get Google OAuth authorization URL"""
    params = {
        'client_id': settings.GOOGLE_CLIENT_ID,
        'redirect_uri': settings.GOOGLE_REDIRECT_URI,
        'scope': 'openid email profile',
        'response_type': 'code',
        'access_type': 'offline',
        'prompt': 'consent'
    }
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    
    return {"auth_url": auth_url}

@router.post("/google/login", response=TokenResponse)
def google_login(request, payload: GoogleLoginRequest):
    """Login with Google OAuth code"""
    try:
        token_url = 'https://oauth2.googleapis.com/token'
        token_data = {
            'client_id': settings.GOOGLE_CLIENT_ID,
            'client_secret': settings.GOOGLE_CLIENT_SECRET,
            'code': payload.code,
            'grant_type': 'authorization_code',
            'redirect_uri': settings.GOOGLE_REDIRECT_URI,
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        try:
            import base64
            cid = settings.GOOGLE_CLIENT_ID or ""
            csec = settings.GOOGLE_CLIENT_SECRET or ""
            basic = base64.b64encode(f"{cid}:{csec}".encode()).decode()
            headers['Authorization'] = f"Basic {basic}"
        except Exception:
            pass

        token_response = requests.post(token_url, data=token_data, headers=headers, timeout=15)
        token_json = token_response.json()
        
        if 'access_token' not in token_json:
            debug = {
                "endpoint": token_url,
                "status_code": token_response.status_code,
                "details": token_json,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "client_id_suffix": (settings.GOOGLE_CLIENT_ID or "")[::-1][:16][::-1],
            }
            return Response({"error": "Failed to get access token from Google", **debug}, status=400)
        
        # Get user info from Google
        google_user_info = get_user_info_from_google(token_json['access_token'])
        
        # Create or get user
        user = create_or_get_user_from_google(google_user_info)
        
        # Create JWT tokens
        tokens = create_jwt_token(user)
        
        return TokenResponse(
            access_token=tokens['access_token'],
            refresh_token=tokens['refresh_token'],
            user={
                'id': user.id,
                'email': user.email,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name
            }
        )
        
    except Exception as e:
        return Response(
            {"error": f"Google login failed: {str(e)}"}, 
            status=400
        )


def _client_ids() -> List[str]:
    val = getattr(settings, 'GOOGLE_CLIENT_ID', None)
    if not val:
        return []
    return [c.strip() for c in str(val).split(',') if c.strip()]


@router.post("/google/login-id-token", response=TokenResponse)
def google_login_id_token(request, payload: GoogleIdTokenRequest):
    """Login with Google ID token (verify locally, no token exchange).

    Useful for frontends using Google Identity Services to obtain an ID token.
    """
    try:
        try:
            from google.oauth2 import id_token as g_id_token
            from google.auth.transport import requests as g_requests
        except Exception as exc:  # pragma: no cover
            return Response({
                "error": "Missing dependency 'google-auth'",
                "hint": "pip install google-auth"
            }, status=500)

        client_ids = _client_ids()
        if not client_ids:
            return Response({"error": "GOOGLE_CLIENT_ID is not configured"}, status=500)

        req = g_requests.Request()
        idinfo = None
        last_exc = None
        for aud in client_ids:
            try:
                idinfo = g_id_token.verify_oauth2_token(payload.id_token, req, aud)
                if idinfo:
                    break
            except Exception as ve:
                last_exc = ve
                continue
        if not idinfo:
            msg = str(last_exc) if last_exc else "Invalid Google ID token"
            return Response({"error": msg}, status=400)

        # Normalize fields similar to userinfo endpoint
        google_user_info = {
            'sub': idinfo.get('sub'),
            'email': idinfo.get('email'),
            'name': idinfo.get('name'),
            'given_name': idinfo.get('given_name'),
            'family_name': idinfo.get('family_name'),
            'picture': idinfo.get('picture'),
        }
        user = create_or_get_user_from_google(google_user_info)

        tokens = create_jwt_token(user)
        return TokenResponse(
            access_token=tokens['access_token'],
            refresh_token=tokens['refresh_token'],
            user={
                'id': user.id,
                'email': user.email,
                'username': user.username,
                'first_name': getattr(user, 'first_name', None),
                'last_name': getattr(user, 'last_name', None),
            }
        )
    except Exception as e:
        return Response({"error": f"Google ID token login failed: {e}"}, status=400)

@router.post("/login", response=TokenResponse)
def login(request, payload: LoginRequest):
    """Traditional email/password login"""
    try:
        user = authenticate(username=payload.email, password=payload.password)
        
        if not user:
            return Response(
                {"error": "Invalid email or password"}, 
                status=401
            )
        
        if not user.is_active:
            return Response(
                {"error": "Account is disabled"}, 
                status=401
            )
        
        # Create JWT tokens
        tokens = create_jwt_token(user)
        
        return TokenResponse(
            access_token=tokens['access_token'],
            refresh_token=tokens['refresh_token'],
            user={
                'id': user.id,
                'email': user.email,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name
            }
        )
        
    except Exception as e:
        return Response(
            {"error": f"Login failed: {str(e)}"}, 
            status=400
        )

@router.get("/profile")
def get_profile(request):
    """Get current user profile (requires authentication)"""
    try:
        return {
            'id': request.auth.id,
            'email': request.auth.email,
            'username': request.auth.username,
            'first_name': request.auth.first_name,
            'last_name': request.auth.last_name,
            'date_joined': request.auth.date_joined
        }
    except Exception as e:
        return Response(
            {"error": f"Failed to get profile: {str(e)}"}, 
            status=400
        )
