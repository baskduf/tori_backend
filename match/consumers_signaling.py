# yourapp/consumers_signaling.py
from channels.generic.websocket import AsyncWebsocketConsumer
import json
import logging

logger = logging.getLogger(__name__)

class VoiceChatSignalingConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_anonymous:
            logger.warning("[CONNECT] Anonymous user attempted connection, rejecting")
            await self.close()
            return
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f"voicechat_{self.room_name}"

        # 그룹에 자신 추가
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        logger.info(f"[CONNECT] User {self.user.id} connected to voicechat room {self.room_name}")

        # 방 이름에서 상대방 user_id 추출
        user_ids = self.room_name.split("_")
        other_user_id = int(user_ids[0]) if int(user_ids[1]) == self.user.id else int(user_ids[1])
        logger.info(f"[CONNECT] Other user id inferred from room name: {other_user_id}")

        # 역할 결정
        if self.user.id < other_user_id:
            role_self = "offer"
            role_other = "answer"
        else:
            role_self = "answer"
            role_other = "offer"
        logger.info(f"[CONNECT] Role assignment: self={role_self}, other={role_other}")

        # 나 자신에게 역할 전송
        await self.send(text_data=json.dumps({
            "type": "role_assignment",
            "role": role_self
        }))
        logger.info(f"[CONNECT] Sent role_assignment to self: {role_self}")

        # 상대방에게 역할 전송
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "role_assignment_message",
                "role": role_other,
                "sender_id": self.user.id
            }
        )
        logger.info(f"[CONNECT] Sent role_assignment_message to other: {role_other}")

    # 그룹 메시지 핸들러
    async def role_assignment_message(self, event):
        # 자신이 보낸 메시지는 무시
        if event.get("sender_id") == self.user.id:
            return

        await self.send(text_data=json.dumps({
            "type": "role_assignment",
            "role": event["role"]
        }))

    async def disconnect(self, close_code):
        try:
            room_group = getattr(self, 'room_group_name', None)
            user = getattr(self, 'user', None)

            if room_group and user and not user.is_anonymous:
                await self.channel_layer.group_discard(room_group, self.channel_name)
                logger.info(f"[DISCONNECT] User {user.id} disconnected from room {room_group}")

                # 매칭 취소 알림
                await self.channel_layer.group_send(
                    room_group,
                    {
                        "type": "match_cancelled",
                        "from_user": getattr(user, 'username', 'unknown'),
                        "user_id": getattr(user, 'id', 0),
                    }
                )
        except Exception as e:
            logger.error(f"Error in disconnect: {e}")

    async def force_disconnect(self, event):
        reason = event.get("reason", "unknown")
        logger.info(f"[SIGNALING] Force disconnect due to: {reason}")
        await self.close()

    async def match_cancelled(self, event):
        await self.send(text_data=json.dumps({
            "type": "match_cancelled",
            "from": event["from_user"]
        }))

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get('type')

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
