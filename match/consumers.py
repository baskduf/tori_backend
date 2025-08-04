# match/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import MatchQueue, MatchRequest, MatchSetting
from django.contrib.auth import get_user_model

User = get_user_model()

class MatchConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        if self.scope["user"].is_anonymous:
            await self.close()
        else:
            self.user = self.scope["user"]
            await self.accept()
            await self.enter_queue()

    async def disconnect(self, close_code):
        await self.exit_queue()

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get("action")

        if action == "heartbeat":
            await self.update_heartbeat()
        elif action == "decision":
            await self.handle_decision(data)

    @database_sync_to_async
    def enter_queue(self):
        MatchQueue.objects.update_or_create(
            user=self.user,
            defaults={"is_active": True}
        )

    @database_sync_to_async
    def update_heartbeat(self):
        MatchQueue.objects.filter(user=self.user).update()

    @database_sync_to_async
    def exit_queue(self):
        MatchQueue.objects.filter(user=self.user).update(is_active=False)

    @database_sync_to_async
    def handle_decision(self, data):
        match_id = data.get("match_id")
        decision = data.get("decision")  # "accept" or "reject"
        # MatchRequest 업데이트 처리
