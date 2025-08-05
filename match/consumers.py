from channels.generic.websocket import AsyncWebsocketConsumer
import json
from .services import MatchService

class MatchConsumer(AsyncWebsocketConsumer):

    async def send_json(self, content):
        await self.send(text_data=json.dumps(content))

    async def connect(self):
        if self.scope["user"].is_anonymous:
            await self.close()
            return

        self.user = self.scope["user"]
        self.group_name = f"user_{self.user.id}"
        self.service = MatchService(self.user)

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.service.remove_from_queue()
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

        matches = await self.service.get_current_match_requests()
        if matches:
            for match in matches:
                partner = await self.service.get_partner(match)
                if partner:
                    await self.channel_layer.group_send(
                        f"user_{partner.id}",
                        {
                            "type": "match_cancelled",
                            "from": self.user.username
                        }
                    )
            await self.service.cleanup_matches(matches)

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get("action")

        if action == "join_queue":
            await self.service.add_to_queue()
            await self.try_match()
        elif action == "respond":
            await self.handle_response(data)

    async def try_match(self):
        my_setting = await self.service.get_my_setting()
        if not my_setting:
            return
        target = await self.service.get_eligible_user(my_setting)
        if target:
            await self.service.create_match_request(target)

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

    async def notify_match(self, event):
        await self.send_json({
            "type": "match_found",
            "partner": event["partner"]
        })

    async def handle_response(self, data):
        partner_name = data.get("partner")
        response = data.get("response")

        if not partner_name or not response:
            return

        match = await self.service.get_match_request(partner_name)
        if not match:
            return

        result, other_user = await self.service.update_match_status_and_create_room(match, response)

        await self.send_json({
            "type": "match_response",
            "result": response
        })

        partner = await self.service.get_partner(match)

        await self.channel_layer.group_send(
            f"user_{partner.id}",
            {
                "type": "match_result",
                "result": response,
                "from": self.user.username
            }
        )

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
