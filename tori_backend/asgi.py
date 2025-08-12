import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tori_backend.settings')
django.setup()  # settings가 로드되고 앱이 준비됨

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application
import match.routing

from match.models import RecentMatchExclude, MatchQueue, MatchRequest, MatchedRoom
from .middleware import JwtAuthMiddleware


def clear_match_data():
    RecentMatchExclude.objects.all().delete()
    MatchQueue.objects.all().delete()
    MatchRequest.objects.all().delete()
    MatchedRoom.objects.all().delete()

# 데이터 클리어 호출 (서버 시작 시 1회 실행)
clear_match_data()

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": JwtAuthMiddleware(
        URLRouter(
            match.routing.websocket_urlpatterns
        )
    ),
})
