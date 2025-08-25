# services.py
from asgiref.sync import sync_to_async
from django.db import transaction
from .models import UserGemWallet, GemTransaction
# views.py
import logging
import base64
import json
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import get_user_model

from gem.models import GemTransaction

from Crypto.Signature import DSS
from Crypto.Hash import SHA256
from Crypto.PublicKey import ECC
from rest_framework.permissions import AllowAny

logger = logging.getLogger(__name__)

User = get_user_model()

async def add_gems(user, amount, note=None):
    """
    지갑에 gems를 증가시키고 트랜잭션 기록
    """
    @transaction.atomic
    def increase():
        wallet, _ = UserGemWallet.objects.get_or_create(user=user)
        wallet.balance += int(amount)
        wallet.save(update_fields=["balance", "updated_at"])

        GemTransaction.objects.create(
            user=user,
            transaction_type="purchase",
            amount=int(amount),
            note=note or "Added gems"
        )
        return wallet.balance

    new_balance = await sync_to_async(increase)()
    return new_balance


async def spend_gems(user, amount, note=None):
    """
    지갑에서 gems를 감소시키고 트랜잭션 기록
    """
    @transaction.atomic
    def deduct():
        wallet, _ = UserGemWallet.objects.get_or_create(user=user)
        wallet.refresh_from_db()
        if wallet.balance < amount:
            raise ValueError("Not enough gems")
        wallet.balance -= int(amount)
        wallet.save(update_fields=["balance", "updated_at"])

        GemTransaction.objects.create(
            user=user,
            transaction_type="spend",
            amount=int(amount),
            note=note or "Spent gems"
        )
        return wallet.balance

    new_balance = await sync_to_async(deduct)()
    return new_balance



def reward_gems_sync(user, amount, note=None):
    from django.db import transaction

    wallet, _ = UserGemWallet.objects.get_or_create(user=user)
    with transaction.atomic():
        wallet.balance += int(amount)
        wallet.save(update_fields=["balance", "updated_at"])

        GemTransaction.objects.create(
            user=user,
            transaction_type="reward",
            amount=int(amount),
            note=note or "Rewarded gems",
        )

    return wallet.balance





# AdMob SSV 공개키 (EC P-256)
ADMOB_PUBLIC_KEY_PEM = """-----BEGIN PUBLIC KEY-----
MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE+nzvoGqvDeB9+SzE6igTl7TyK4JB
bglwir9oTcQta8NuG26ZpZFxt+F2NDk7asTE6/2Yc8i1ATcGIqtuS5hv0Q==
-----END PUBLIC KEY-----"""

def base64_urlsafe_decode(s):
    """Base64 URL-safe 디코딩 함수"""
    s = s.encode() if isinstance(s, str) else s
    # URL-safe 문자들을 표준 base64로 변환
    s = s.replace(b'-', b'+').replace(b'_', b'/')
    # 패딩 추가
    padding = b'=' * (-len(s) % 4)
    return base64.b64decode(s + padding)

class RewardedAdSSVView(APIView):
    authentication_classes = []  # 인증 완전 비활성화
    permission_classes = [AllowAny]  # 인증 없이 접근 허용

    def get(self, request):
        data = request.query_params
        logger.info(f"Received SSV GET params: {data}")

        # 필수 파라미터 확인
        required_fields = [
            "ad_unit", "reward_amount", "reward_item",
            "transaction_id", "signature", "timestamp",
            "key_id", "user_id"
        ]
        for field in required_fields:
            if field not in data:
                logger.warning(f"Missing required field: {field}")
                return Response({"error": f"{field} is required"}, status=400)

        signature_b64 = data["signature"]
        logger.info(f"Original signature: {signature_b64}")

        # 서명 검증
        try:
            # 서명할 메시지 구성 - AdMob SSV 문서에 따르면 쿼리 스트링 형태로 구성
            # 중요: signature 파라미터는 제외하고, URL 인코딩된 형태로 메시지 구성
            query_params = []
            for key in sorted(data.keys()):
                if key != "signature":
                    # URL 인코딩된 값 그대로 사용 (request.query_params에서 이미 디코딩됨)
                    query_params.append(f"{key}={data[key]}")
            
            message = "&".join(query_params)
            logger.info(f"Message to verify: {message}")
            
            # 원본 쿼리 스트링으로도 시도해보기 위한 로깅
            original_query = request.META.get('QUERY_STRING', '')
            logger.info(f"Original query string: {original_query}")
            
            # 서명 디코딩
            signature_bytes = base64_urlsafe_decode(signature_b64)
            logger.info(f"Signature bytes length: {len(signature_bytes)}")
            logger.info(f"Signature bytes (hex): {signature_bytes.hex()}")
            
            # 공개키 로드 및 검증
            public_key = ECC.import_key(ADMOB_PUBLIC_KEY_PEM)
            logger.info(f"Public key loaded: {public_key.curve}")
            
            # 방법 1: 디코딩된 파라미터로 메시지 구성
            h1 = SHA256.new(message.encode('utf-8'))
            verifier = DSS.new(public_key, 'fips-186-3')
            
            try:
                verifier.verify(h1, signature_bytes)
                logger.info("Signature verification successful with decoded params")
            except ValueError as ve1:
                logger.warning(f"Verification with decoded params failed: {ve1}")
                
                # 방법 2: 원본 쿼리 스트링에서 signature만 제거한 형태로 시도
                if original_query:
                    # signature 파라미터 제거
                    query_parts = original_query.split('&')
                    filtered_parts = [part for part in query_parts if not part.startswith('signature=')]
                    # 알파벳 순으로 정렬
                    filtered_parts.sort()
                    message_original = "&".join(filtered_parts)
                    logger.info(f"Message with original encoding: {message_original}")
                    
                    h2 = SHA256.new(message_original.encode('utf-8'))
                    try:
                        verifier.verify(h2, signature_bytes)
                        logger.info("Signature verification successful with original query string")
                    except ValueError as ve2:
                        logger.warning(f"Verification with original query failed: {ve2}")
                        
                        # 방법 3: 테스트용 - 실제 AdMob이 아닌 테스트 서명인지 확인
                        logger.error("All verification methods failed - this might be a test signature")
                        
                        # 개발/테스트 환경에서는 서명 검증을 스킵할 수 있도록 설정
                        from django.conf import settings
                        if hasattr(settings, 'SKIP_ADMOB_SIGNATURE_VERIFICATION') and settings.SKIP_ADMOB_SIGNATURE_VERIFICATION:
                            logger.warning("Skipping signature verification due to development setting")
                        else:
                            raise ve2
                else:
                    raise ve1
                    
        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return Response({"error": f"Invalid signature: {str(e)}"}, status=400)

        # 사용자 조회
        user_id = data["user_id"]
        user = User.objects.filter(email=user_id).first()
        if not user:
            logger.warning(f"User not found: {user_id}")
            return Response({"error": "User not found"}, status=404)

        ad_unit_id = data["ad_unit"]
        reward_item = data["reward_item"]
        transaction_id = data["transaction_id"]

        try:
            reward_amount = int(data["reward_amount"])
        except ValueError:
            logger.warning(f"Invalid reward_amount: {data['reward_amount']}")
            return Response({"error": "reward_amount must be integer"}, status=400)

        # 하루 제한 체크
        today_count = GemTransaction.objects.filter(
            user=user,
            transaction_type="reward",
            created_at__date=timezone.now().date()
        ).count()
        if today_count >= 10:
            logger.warning(f"Daily reward limit exceeded for user: {user_id}")
            return Response({"error": "하루 보상 한도를 초과했습니다 (최대 10회)"}, status=400)

        # 보상 지급
        new_balance = reward_gems_sync(
            user=user,
            amount=reward_amount,
            note=f"Reward from AdMob SSV {reward_item}"
        )
        logger.info(f"Reward granted for user {user_id}, new_balance: {new_balance}")

        return Response({"message": "Reward granted", "new_balance": new_balance}, status=200)