from django.http import JsonResponse
from django.conf import settings
import requests
import base64


def oauth_callback(request):
    """Google OAuth redirect handler (JSON only).

    Exchanges the authorization code for an access token, fetches Google user info,
    creates or updates the user in DB, and returns JSON (no templates, no Blade).
    """
    # Reuse helper logic from the API module
    from .api import (
        get_user_info_from_google,
        create_or_get_user_from_google,
        create_jwt_token,
    )

    error = request.GET.get("error")
    if error:
        return JsonResponse({"error": error}, status=400)

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
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        
        # Debug: Log what we're sending to Google
        print(f"DEBUG - Google OAuth Request:")
        print(f"  Client ID: {settings.GOOGLE_CLIENT_ID}")
        print(f"  Client Secret: {settings.GOOGLE_CLIENT_SECRET[:10]}...")
        print(f"  Redirect URI: {settings.GOOGLE_REDIRECT_URI}")
        print(f"  Code: {code[:20]}...")
        
        token_response = requests.post(token_url, data=token_data, headers=headers, timeout=15)
        token_json = token_response.json()
        
        print(f"DEBUG - Google Response: {token_json}")
        
        access_token = token_json.get("access_token")
        if not access_token:
            debug = {
                "error": "Failed to get access token from Google",
                "endpoint": token_url,
                "status_code": token_response.status_code,
                "details": token_json,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "request_path": request.get_full_path(),
                "client_id_suffix": (settings.GOOGLE_CLIENT_ID or "")[::-1][:16][::-1],
                "sent_data": {
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                    "has_secret": bool(settings.GOOGLE_CLIENT_SECRET),
                    "secret_length": len(settings.GOOGLE_CLIENT_SECRET or "")
                }
            }
            return JsonResponse(debug, status=400)

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
