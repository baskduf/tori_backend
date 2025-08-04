# your_project/routing.py
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import match.routing

application = ProtocolTypeRouter({
    "websocket": AuthMiddlewareStack(
        URLRouter(
            match.routing.websocket_urlpatterns
        )
    ),
})

from django.urls import re_path
from match.consumers import MatchConsumer  # 본인 컨슈머 경로에 맞게 수정

websocket_urlpatterns = [
    re_path(r'ws/match/$', MatchConsumer.as_asgi()),
]