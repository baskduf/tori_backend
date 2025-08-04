# tori_backend/asgi.py 예시

import os
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application
import match.routing  # match app의 websocket 라우팅

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tori_backend.settings')

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            match.routing.websocket_urlpatterns
        )
    ),
})
