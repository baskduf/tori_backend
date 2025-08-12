# yourapp/consumers_signaling.py
from channels.generic.websocket import AsyncWebsocketConsumer
import json
import logging

logger = logging.getLogger(__name__)

class VoiceChatSignalingConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        
        self.user = self.scope["user"]
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f"voicechat_{self.room_name}"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        logger.info(f"User connected to voicechat room {self.room_name}")


    async def disconnect(self, close_code):
        try:
            # 방 그룹에서 자신 제거
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
            logger.info(f"User {self.user.id} disconnected from room {self.room_name}")

            # 같은 방에 속한 다른 사용자들에게 매칭 취소 알림 전송
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "match_cancelled",  # 이 메서드 이름은 아래에 구현 필요
                    "from_user": self.user.username,
                    "user_id": self.user.id,
                }
            )
        except Exception as e:
            logger.error(f"Error in disconnect: {e}")

    # 그리고 그룹 메시지 핸들러 예시:
    async def match_cancelled(self, event):
        await self.send(text_data=json.dumps({
            "type": "match_cancelled",
            "from": self.user.username
        }))


    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get('type')

        # 예: 시그널링 메시지 유형별 로깅 또는 추가 처리 가능
        if msg_type in ['offer', 'answer', 'ice-candidate']:
            logger.info(f"Received {msg_type} from {self.channel_name} in room {self.room_name}")
        else:
            logger.info(f"Received unknown type {msg_type}")

        # 현재는 그룹에 그대로 전달
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "signal_message",
                "message": data,
                "sender_channel": self.channel_name,
            }
        )


    async def signal_message(self, event):
        if event["sender_channel"] == self.channel_name:
            return
        await self.send(text_data=json.dumps(event["message"]))
