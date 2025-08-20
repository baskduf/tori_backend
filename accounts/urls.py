# accounts/urls.py
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    LogoutView,
    UserProfileView,
    SocialLoginCodeView,
    SocialSignupView,
    MobileGoogleLoginView
)

urlpatterns = [
    # 일반 JWT 회원가입 / 로그인 / 토큰 갱신 / 로그아웃
    path('signup/', SocialSignupView.as_view(), name='signup'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),

    # 회원 정보 조회/수정
    path('profile/', UserProfileView.as_view(), name='profile'),

    # urls.py
    path('oauth/<str:provider>/code', SocialLoginCodeView.as_view()),

    path('mobile/google-login/', MobileGoogleLoginView.as_view(), name='google-login'),
]
