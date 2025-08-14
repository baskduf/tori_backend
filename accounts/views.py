import requests
from django.conf import settings
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import RetrieveUpdateAPIView
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import SignUpSerializer, UserSerializer, UserUpdateSerializer

User = get_user_model()

class SignUpAndGetTokenView(APIView):
    """
    회원가입 시 Google reCAPTCHA 검증 추가
    """
    def post(self, request):
        captcha_token = request.data.get("recaptcha_token")
        if not captcha_token:
            return Response({"error": "CAPTCHA token is required."},
                            status=status.HTTP_400_BAD_REQUEST)

        # Google reCAPTCHA 검증
        captcha_verified = self.verify_captcha(captcha_token)
        if not captcha_verified:
            return Response({"error": "CAPTCHA verification failed."},
                            status=status.HTTP_400_BAD_REQUEST)

        serializer = SignUpSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'username': user.username
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def verify_captcha(self, token):
        """
        Google reCAPTCHA 서버 검증 요청
        """
        secret_key = settings.RECAPTCHA_SECRET_KEY
        try:
            response = requests.post(
                "https://www.google.com/recaptcha/api/siteverify",
                data={"secret": secret_key, "response": token}
            )
            result = response.json()
            return result.get("success", False)
        except requests.RequestException:
            return False


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"message": "Logout successful."}, status=status.HTTP_205_RESET_CONTENT)
        except Exception:
            return Response({"error": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return UserUpdateSerializer
        return UserSerializer
