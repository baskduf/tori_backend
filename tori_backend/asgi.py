import os
import django
import logging
import redis

# 1. Django 설정 로드
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tori_backend.settings.dev")
django.setup()

# 2. 로깅 설정
logger = logging.getLogger(__name__)

# 3. 모델 임포트
from match.models import MatchQueue, MatchRequest, MatchedRoom
from django.db import transaction

# 4. Redis 초기화
REDIS_HOST = "localhost"  # 필요시 환경변수로 관리
REDIS_PORT = 6379
REDIS_DB = 0

redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

def clear_redis_cache():
    """Redis 캐시 전체 삭제 (매칭 관련)"""
    try:
        redis_client.flushdb()
        logger.info("Redis cache cleared")
    except Exception as e:
        logger.error(f"Redis clear failed: {e}")

# 5. DB 초기화
def clear_match_data():
    """DB 매칭 관련 테이블 초기화"""
    try:
        with transaction.atomic():
            cleared_queue = MatchQueue.objects.all().delete()
            cleared_requests = MatchRequest.objects.all().delete()
            cleared_rooms = MatchedRoom.objects.all().delete()
            logger.info(f"Cleared DB: MatchQueue={cleared_queue}, MatchRequest={cleared_requests}, MatchedRoom={cleared_rooms}")
    except Exception as e:
        logger.error(f"DB clear failed: {e}")

# 6. 초기화 실행
clear_match_data()
clear_redis_cache()

# 7. ASGI 설정
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application
import match.routing
from .middleware import JwtAuthMiddleware

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        JwtAuthMiddleware(
            URLRouter(
                match.routing.websocket_urlpatterns
            )
        )
    ),
})
