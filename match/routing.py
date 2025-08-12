from django.urls import re_path
from . import consumers
from . import consumers_signaling

websocket_urlpatterns = [
    re_path(r"ws/match/$", consumers.MatchConsumer.as_asgi()),
    re_path(r"ws/voicechat/(?P<room_name>\w+)/$", consumers_signaling.VoiceChatSignalingConsumer.as_asgi()),
]
