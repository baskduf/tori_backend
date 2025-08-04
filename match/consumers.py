import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from django.utils import timezone
from .models import MatchQueue, MatchRequest
from django.contrib.auth import get_user_model

User = get_user_model()

class MatchConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        print(f"[connect] User {self.scope['user']} is connecting...")
        if self.scope["user"].is_anonymous:
            print("[connect] Anonymous user, connection rejected")
            await self.close()
            return
        self.user = self.scope["user"]
        self.group_name = f"user_{self.user.id}"

        # 유저별 그룹에 가입 (상대방에게 메시지 보내기 위해)
        await self.channel_layer.group_add(self.group_name, self.channel_name)

        await self.accept()
        print(f"[connect] User {self.user.username} connected and accepted.")
        await self.enter_queue()

    async def disconnect(self, close_code):
        print(f"[disconnect] User {self.user.username} disconnected.")
        await self.exit_queue()
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        print(f"[receive] user:{self.user.username} message: {text_data}")
        data = json.loads(text_data)
        action = data.get("action")
        print(f"[receive] action: {action}")

        if action == "heartbeat":
            await self.update_heartbeat()
        elif action == "decision":
            await self.handle_decision(data)
        elif action == "enter_queue":
            await self.enter_queue()
            await self.try_match()

    @database_sync_to_async
    def enter_queue(self):
        print(f"[enter_queue] User {self.user.username} entering queue")
        MatchQueue.objects.update_or_create(
            user=self.user,
            defaults={
                "is_active": True,
                "last_heartbeat": timezone.now(),
            }
        )

    @database_sync_to_async
    def update_heartbeat(self):
        print(f"[update_heartbeat] User {self.user.username} heartbeat updated")
        MatchQueue.objects.filter(user=self.user).update(last_heartbeat=timezone.now())

    @database_sync_to_async
    def exit_queue(self):
        print(f"[exit_queue] User {self.user.username} exiting queue")
        MatchQueue.objects.filter(user=self.user).update(is_active=False)

    @database_sync_to_async
    def handle_decision(self, data):
        match_id = data.get("match_id")
        decision = data.get("decision")  # "accept" or "reject"
        print(f"[handle_decision] User {self.user.username} decision: {decision} for match_id: {match_id}")

        try:
            # 매칭 수락/거절은 matched_user가 결정을 하므로 matched_user=self.user로 조회
            match_request = MatchRequest.objects.get(id=match_id, matched_user=self.user)
            if decision == "accept":
                match_request.status = "accepted"
            elif decision == "reject":
                match_request.status = "rejected"
            match_request.save()
            print(f"[handle_decision] MatchRequest {match_id} updated to {match_request.status}")
        except MatchRequest.DoesNotExist:
            print(f"[handle_decision] MatchRequest {match_id} does not exist or user mismatch")

    async def try_match(self):
        print(f"[try_match] Trying to find a match for user {self.user.username}")
        matched_user = await self.find_match()
        if matched_user:
            print(f"[try_match] Found matched user: {matched_user.username}")
            match_request = await database_sync_to_async(MatchRequest.objects.create)(
                requester=self.user,
                matched_user=matched_user,
                status="pending"
            )
            channel_layer = get_channel_layer()

            # 내 쪽에 매칭 알림 전송
            await self.send(text_data=json.dumps({
                "action": "match_found",
                "matched_username": matched_user.username,
                "match_id": match_request.id,
            }))

            # 상대방 쪽에 매칭 알림 전송
            await channel_layer.group_send(
                f"user_{matched_user.id}",
                {
                    "type": "match.found",
                    "matched_username": self.user.username,
                    "match_id": match_request.id,
                }
            )
        else:
            print(f"[try_match] No matched user found for {self.user.username}")

    @database_sync_to_async
    def find_match(self):
        candidates = list(MatchQueue.objects.filter(is_active=True).exclude(user=self.user))
        if candidates:
            return candidates[0].user
        return None

    async def match_found(self, event):
        print(f"[match_found] Received match found event: {event}")
        await self.send(text_data=json.dumps({
            "action": "match_found",
            "matched_username": event["matched_username"],
            "match_id": event["match_id"],
        }))
