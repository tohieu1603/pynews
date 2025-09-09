from ninja import Router
from ninja.responses import Response
from pydantic import BaseModel# Authentication endpoints
@router.get("/google/auth-url", response=GoogleAuthUrlResponse)
def get_google_auth_url(request):
    """Get Google OAuth authorization URL"""
    from urllib.parse import urlencode
    
    params = {
        'client_id': settings.GOOGLE_CLIENT_ID,
        'redirect_uri': settings.GOOGLE_REDIRECT_URI,
        'scope': 'openid email profile',
        'response_type': 'code',
        'access_type': 'offline',
        'prompt': 'consent'
    }
    
    auth_url = f"https://accounts.google.com/o/oauth2/auth?{urlencode(params)}"
    
    return {"auth_url": auth_url}
from authlib.integrations.requests_client import OAuth2Session
from django.conf import settings
import jwt
import datetime
import requests
from typing import Optional

User = get_user_model()
router = Router()

# Pydantic schemas
class LoginRequest(BaseModel):
    email: str
    password: str

class GoogleLoginRequest(BaseModel):
    code: str

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
    access_payload = {
        'user_id': user.id,
        'email': user.email,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=settings.JWT_ACCESS_TTL_MIN),
        'iat': datetime.datetime.utcnow(),
        'type': 'access'
    }
    
    refresh_payload = {
        'user_id': user.id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=settings.JWT_REFRESH_TTL_DAYS),
        'iat': datetime.datetime.utcnow(),
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
        raise Exception("Failed to get user info from Google")
    
    return response.json()

def create_or_get_user_from_google(google_user_info: dict):
    """Create or get user from Google user information"""
    google_id = google_user_info.get('id')
    email = google_user_info.get('email')
    name = google_user_info.get('name', '')
    avatar_url = google_user_info.get('picture', '')
    
    # Check if user exists with this email
    user = User.objects.filter(email=email).first()
    
    if user:
        # Update user info if needed
        if not user.first_name and name:
            user.first_name = name
            user.save()
        return user
    
    # Create new user
    user = User.objects.create_user(
        username=email,
        email=email,
        first_name=name
    )
    
    return user

# Authentication endpoints
@router.get("/google/auth-url", response=GoogleAuthUrlResponse)
def get_google_auth_url(request):
    """Get Google OAuth authorization URL"""
    oauth = OAuth2Session(
        settings.GOOGLE_CLIENT_ID,
        redirect_uri=settings.GOOGLE_REDIRECT_URI
    )
    
    authorization_url, state = oauth.authorization_url(
        'https://accounts.google.com/o/oauth2/auth',
        scope=['openid', 'email', 'profile']
    )
    
    return {"auth_url": authorization_url}

@router.post("/google/login", response=TokenResponse)
def google_login(request, payload: GoogleLoginRequest):
    """Login with Google OAuth code"""
    try:
        # Exchange authorization code for access token
        oauth = OAuth2Session(
            settings.GOOGLE_CLIENT_ID,
            redirect_uri=settings.GOOGLE_REDIRECT_URI
        )
        
        token = oauth.fetch_token(
            'https://oauth2.googleapis.com/token',
            authorization_response=None,
            code=payload.code,
            client_secret=settings.GOOGLE_CLIENT_SECRET
        )
        
        # Get user info from Google
        google_user_info = get_user_info_from_google(token['access_token'])
        
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
