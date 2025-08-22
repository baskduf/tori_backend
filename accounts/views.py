# accounts/views.py
import jwt
import requests
import logging
from django.conf import settings
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import RetrieveUpdateAPIView
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from match.models import MatchSetting

logger = logging.getLogger(__name__)
User = get_user_model()


# ==========================
# Google 소셜 로그인 처리
# ==========================
class SocialLoginCodeView(APIView):
    def post(self, request, *args, **kwargs):
        provider = request.data.get("provider")
        code = request.data.get("code")

        if not provider or not code:
            return Response({"error": "provider와 code가 필요합니다."},
                            status=status.HTTP_400_BAD_REQUEST)

        # === Google OAuth 토큰 교환 ===
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            "code": code,
            "client_id": settings.GOOGLE_OAUTH2_CLIENT_ID,
            "client_secret": settings.GOOGLE_OAUTH2_CLIENT_SECRET,
            "redirect_uri": settings.LOGIN_REDIRECT_URL,  # 콘솔과 동일하게
            "grant_type": "authorization_code",
        }

        logger.info(f"Token request data: {token_data}")
        try:
            token_res = requests.post(token_url, data=token_data)
            logger.info(f"Token response status: {token_res.status_code}")
            logger.info(f"Token response body: {token_res.text}")
            token_json = token_res.json()
        except Exception as e:
            logger.error(f"Token 요청 오류: {e}")
            return Response({"error": "토큰 요청 실패"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        access_token = token_json.get("access_token")
        if not access_token:
            logger.warning(f"토큰 발급 실패: {token_json}")
            return Response({"error": "구글 토큰 발급 실패"},
                            status=status.HTTP_400_BAD_REQUEST)

        # === 사용자 정보 가져오기 ===
        try:
            user_info = requests.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            ).json()
        except Exception as e:
            logger.error(f"User info 요청 실패: {e}")
            return Response({"error": "사용자 정보 요청 실패"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        email = user_info.get("email")
        name = user_info.get("name", "")
        picture = user_info.get("picture", "")

        if not email:
            return Response({"error": "이메일을 가져올 수 없음"},
                            status=status.HTTP_400_BAD_REQUEST)

        # === 기존 유저 확인 ===
        try:
            user = User.objects.get(email=email)
            refresh = RefreshToken.for_user(user)
            return Response({
                "statusCode": 200,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            }, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            # 신규 회원 → temp_token 발급
            payload = {"email": email, "provider": provider}
            temp_token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
            return Response({
                "statusCode": 202,
                "error": "signup_required",
                "user_data": {"name": name, "profile_url": picture, 
                "temp_token": temp_token,},
            }, status=status.HTTP_202_ACCEPTED)

# ==========================
# 소셜 회원가입 처리 (디버깅 추가)
# ==========================
class SocialSignupView(APIView):
    def post(self, request, *args, **kwargs):
        temp_token = request.data.get("temp_token")
        username = request.data.get("username")
        age = request.data.get("age")
        gender = request.data.get("gender")
        profile_image = request.FILES.get("profile_image")

        logger.info(f"SocialSignupView 요청 데이터: temp_token={temp_token}, username={username}, age={age}, gender={gender}, profile_image={profile_image}")

        if not temp_token or not username:
            logger.warning("필수 값 누락")
            return Response({"error": "필수 값 누락"}, status=status.HTTP_400_BAD_REQUEST)

        # temp_token 검증
        try:
            payload = jwt.decode(temp_token, settings.SECRET_KEY, algorithms=["HS256"])
            logger.info(f"temp_token payload: {payload}")
        except jwt.ExpiredSignatureError:
            logger.warning("토큰 만료됨")
            return Response({"error": "토큰 만료됨"}, status=status.HTTP_400_BAD_REQUEST)
        except jwt.InvalidTokenError:
            logger.warning("잘못된 토큰")
            return Response({"error": "잘못된 토큰"}, status=status.HTTP_400_BAD_REQUEST)

        email = payload.get("email")
        provider = payload.get("provider")
        if not email:
            logger.error("토큰에서 이메일 없음")
            return Response({"error": "토큰에서 이메일 없음"}, status=status.HTTP_400_BAD_REQUEST)

        # 실제 DB에 회원 생성
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                age=age or 18,
                gender=gender or "male",
                password=None,
            )
            MatchSetting.objects.create(
                user=user,
                preferred_gender='any',
                age_min=1,
                age_max=99,
                radius_km=100
            )
            logger.info(f"신규 유저 생성: id={user.id}, email={user.email}")

            if profile_image:
                user.profile_image = profile_image
                user.save()
                logger.info("프로필 이미지 저장 완료")

        except Exception as e:
            logger.error(f"회원 생성 실패: {e}")
            return Response({"error": f"회원 생성 실패: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        refresh = RefreshToken.for_user(user)
        logger.info(f"JWT 발급 완료: access={refresh.access_token}, refresh={refresh}")

        return Response({
            "statusCode": 201,
            "message": "회원가입 성공",
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }, status=status.HTTP_201_CREATED)


# ==========================
# 로그아웃 처리 (디버깅 추가)
# ==========================
class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        logger.info(f"LogoutView 요청: refresh_token={refresh_token}")

        if not refresh_token:
            logger.warning("리프레시 토큰 누락")
            return Response({"detail": "리프레시 토큰 누락"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            logger.info("로그아웃 처리 완료 (토큰 블랙리스트)")
            return Response({"detail": "로그아웃 완료"}, status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            logger.error(f"로그아웃 실패: {e}")
            return Response({"detail": f"잘못된 토큰: {e}"}, status=status.HTTP_400_BAD_REQUEST)


# ==========================
# 프로필 조회/수정 (디버깅 추가)
# ==========================
class UserProfileView(RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            from .serializers import UserUpdateSerializer
            return UserUpdateSerializer
        from .serializers import UserSerializer
        return UserSerializer

    def get_object(self):
        user = self.request.user
        logger.info(f"UserProfileView 호출: user_id={user.id}, email={user.email}")
        return user


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from google.oauth2 import id_token
# from google.auth.transport import requests
from django.contrib.auth import get_user_model

class MobileGoogleLoginView(APIView):
    def post(self, request):
        token = request.data.get("id_token")
        if not token:
            return Response({"error": "No ID token provided"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 구글 서버에서 토큰 검증
            idinfo = id_token.verify_oauth2_token(token, requests.Request(), settings.GOOGLE_OAUTH2_CLIENT_ID)
            email = idinfo.get('email')
            name = idinfo.get('name', '')
            picture = idinfo.get('picture', '')

            if not email:
                return Response({"error": "이메일을 가져올 수 없음"}, status=status.HTTP_400_BAD_REQUEST)

            # 기존 유저 확인
            try:
                user = User.objects.get(email=email)
                refresh = RefreshToken.for_user(user)
                return Response({
                    "statusCode": 200,
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                })
            except User.DoesNotExist:
                # 신규 회원 → 임시 회원가입 처리 (temp_token 발급)
                payload = {"email": email, "provider": "google"}
                temp_token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
                return Response({
                    "statusCode": 202,
                    "error": "signup_required",
                    "user_data": {
                        "name": name,
                        "profile_url": picture,
                        "temp_token": temp_token,
                    },
                }, status=status.HTTP_202_ACCEPTED)

        except ValueError:
            return Response({"error": "Invalid ID token"}, status=status.HTTP_400_BAD_REQUEST)
