from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class MatchConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'match'

    def ready(self):
        from .models import MatchQueue, MatchRequest, MatchedRoom

        # 서버 시작 시 매칭 관련 임시 데이터 삭제
        queue_count, _ = MatchQueue.objects.all().delete()
        request_count, _ = MatchRequest.objects.all().delete()
        room_count, _ = MatchedRoom.objects.all().delete()

        logger.info(
            f"Server start: Cleared MatchQueue={queue_count}, "
            f"MatchRequest={request_count}, MatchedRoom={room_count}"
        )
