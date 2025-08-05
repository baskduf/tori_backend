from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
import json
from .models import MatchQueue, MatchRequest, MatchSetting, MatchedRoom
from django.db.models import Q


User = get_user_model()

class MatchConsumer(AsyncWebsocketConsumer):

    async def send_json(self, content):
        await self.send(text_data=json.dumps(content))

    async def connect(self):
        if self.scope["user"].is_anonymous:
            await self.close()
        else:
            self.user = self.scope["user"]
            self.group_name = f"user_{self.user.id}"

            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()

    async def disconnect(self, close_code):
        await self.remove_from_queue()
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

        matches = await self.get_current_match_requests()
        if matches:
            for match in matches:
                partner = await self.get_partner(match)
                if partner:
                    await self.channel_layer.group_send(
                        f"user_{partner.id}",
                        {
                            "type": "match_cancelled",
                            "from": self.user.username
                        }
                    )
            await self.cleanup_matches(matches)


    @database_sync_to_async
    def get_current_match_requests(self):
        return list(
            MatchRequest.objects.filter(
                Q(from_user=self.user) | Q(to_user=self.user)
            )
        )


    @database_sync_to_async
    def cleanup_matches(self, matches):
        for match in matches:
            match.delete()


    @database_sync_to_async
    def get_current_match_request(self):
        return MatchRequest.objects.filter(
            Q(from_user=self.user) | Q(to_user=self.user)
        ).first()



    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get("action")

        if action == "join_queue":
            await self.add_to_queue()
            await self.try_match()
        elif action == "respond":
            await self.handle_response(data)

    # ----------------- Queue Management ----------------- #

    @database_sync_to_async
    def add_to_queue(self):
        MatchQueue.objects.update_or_create(user=self.user, defaults={"is_active": True})

    @database_sync_to_async
    def remove_from_queue(self):
        MatchQueue.objects.filter(user=self.user).update(is_active=False)

    @database_sync_to_async
    def get_my_setting(self):
        return MatchSetting.objects.filter(user=self.user).first()

    @database_sync_to_async
    def get_eligible_user(self, setting):
        qs = MatchQueue.objects.filter(is_active=True).exclude(user=self.user)
        for mq in qs:
            try:
                other_setting = MatchSetting.objects.get(user=mq.user)
            except MatchSetting.DoesNotExist:
                continue

            if not (setting.age_min <= other_setting.user.age <= setting.age_max):
                continue
            if setting.preferred_gender != 'any' and other_setting.user.gender != setting.preferred_gender:
                continue
            if other_setting.preferred_gender != 'any' and setting.user.gender != other_setting.preferred_gender:
                continue

            return mq.user
        return None

    async def try_match(self):
        my_setting = await self.get_my_setting()
        if not my_setting:
            return
        target = await self.get_eligible_user(my_setting)
        if target:
            await self.create_match_request(target)

            await self.send_json({
                "type": "match_found",
                "partner": target.username
            })

            await self.channel_layer.group_send(
                f"user_{target.id}",
                {
                    "type": "notify_match",
                    "partner": self.user.username
                }
            )
    
    async def match_cancelled(self, event):
        await self.send_json({
            "type": "match_cancelled",
            "from": event.get("from")
        })


    @database_sync_to_async
    def create_match_request(self, other_user):
        MatchRequest.objects.create(from_user=self.user, to_user=other_user, status='matched')
        

    async def notify_match(self, event):
        await self.send_json({
            "type": "match_found",
            "partner": event["partner"]
        })

    # ----------------- Matching Response ----------------- #

    @database_sync_to_async
    def get_match_request(self, partner_name):
        try:
            partner = User.objects.get(username=partner_name)
        except User.DoesNotExist:
            return None

        return MatchRequest.objects.select_related('from_user', 'to_user').filter(
            from_user__in=[self.user, partner],
            to_user__in=[self.user, partner],
            status__in=['matched', 'accepted']
        ).first()
    
    @database_sync_to_async
    def update_match_status_and_create_room(self, match, response):
        other_user = match.to_user if match.from_user == self.user else match.from_user

        if response == 'accept':
            # 내 요청 제외하고 상대가 보낸 accepted 요청 확인
            other_accepted = MatchRequest.objects.filter(
                from_user__in=[self.user, other_user],
                to_user__in=[self.user, other_user],
                status__in=[ 'accepted']
            ).first()

            if other_accepted:
                # 양쪽 다 수락 → 매칭 성사
                match.status = 'success'
                other_accepted.status = 'success'
                match.save()
                other_accepted.save()

                MatchedRoom.objects.create(user1=self.user, user2=other_user)

                # 매칭 요청 삭제
                match.delete()
                other_accepted.delete()

                # 매칭 큐 삭제
                MatchQueue.objects.filter(user__in=[self.user, other_user]).delete()

                return ("success", other_user)
            else:
                # 상대방은 아직 수락 안 함 → 내 요청만 accepted 처리
                match.status = 'accepted'
                match.save()
                return ("accepted", None)

        else:
            # 거절 시 해당 요청 삭제 (상대 요청은 남길 수도 있음)
            match.delete()

            # 매칭 대기열 재활성화
            MatchQueue.objects.filter(user__in=[self.user, other_user]).update(is_active=True)

            return ("rejected", None)


    @database_sync_to_async
    def get_partner(self, match):
        return match.from_user if match.to_user == self.user else match.to_user

    async def handle_response(self, data):
        partner_name = data.get("partner")
        response = data.get("response")

        if not partner_name or not response:
            return

        match = await self.get_match_request(partner_name)
        if not match:
            return

        result, other_user = await self.update_match_status_and_create_room(match, response)

        await self.send_json({
            "type": "match_response",
            "result": response
        })

        partner = await self.get_partner(match)

        await self.channel_layer.group_send(
            f"user_{partner.id}",
            {
                "type": "match_result",
                "result": response,
                "from": self.user.username
            }
        )

        # 양쪽 모두 수락 → 매칭 성사
        if result == "success":
            room_name = f"{min(self.user.id, partner.id)}_{max(self.user.id, partner.id)}"
            await self.send_json({
                "type": "match_success",
                "room": room_name
            })
            await self.channel_layer.group_send(
                f"user_{partner.id}",
                {
                    "type": "match_success",
                    "room": room_name
                }
            )

    async def match_result(self, event):
        await self.send_json({
            "type": "match_response",
            "result": event["result"],
            "from": event["from"]
        })

    async def match_success(self, event):
        await self.send_json({
            "type": "match_success",
            "room": event["room"]
        })
