from pathlib import Path
import os

# --------------------------------
# OAuth 관련 환경 변수
# --------------------------------
GOOGLE_OAUTH2_CLIENT_ID = os.getenv("GOOGLE_OAUTH2_CLIENT_ID")
GOOGLE_OAUTH2_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH2_CLIENT_SECRET")

if not GOOGLE_OAUTH2_CLIENT_ID or not GOOGLE_OAUTH2_CLIENT_SECRET:
    raise ValueError("Google OAuth2 Client ID/Secret must be set in environment variables")

# --------------------------------
# Allauth 기본 설정
# --------------------------------
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_EMAIL_REQUIRED = False
LOGIN_REDIRECT_URL = os.getenv("LOGIN_REDIRECT_URL", "http://localhost:51577")
LOGOUT_REDIRECT_URL = os.getenv("LOGOUT_REDIRECT_URL", "/")
