import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tori_backend.settings')
django.setup()  # settings가 로드되고 앱이 준비됨

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application
import match.routing  # 앱 라우팅은 setup 이후에 import해야 함

django_asgi_app = get_asgi_application()

from .middleware import JwtAuthMiddleware
import match.routing

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": JwtAuthMiddleware(
        URLRouter(
            match.routing.websocket_urlpatterns
        )
    ),
})