from channels.generic.websocket import AsyncWebsocketConsumer
import json
import logging
from .services import MatchService
from django.conf import settings
import asyncio

logger = logging.getLogger(__name__)

class MatchConsumer(AsyncWebsocketConsumer):

    async def send_json(self, content):
        """JSON 응답 전송"""
        try:
            await self.send(text_data=json.dumps(content))
        except Exception as e:
            logger.error(f"Error sending JSON: {e}")

    async def connect(self):
        """연결 시 초기화"""
        if self.scope["user"].is_anonymous:
            await self.close()
            return

        self.user = self.scope["user"]
        self.user_id = str(self.user.id)
        self.group_name = f"user_{self.user.id}"
        self.service = MatchService(self.user)

        try:
            # 중복 로그인 체크
            if await self.service.is_user_online():
                logger.info(f"User {self.user_id} is already online, disconnecting old session")

                await self.channel_layer.group_send(
                    f"user_{self.user_id}",
                    {
                        "type": "force_disconnect",
                        "reason": "new_login"
                    }
                )

                await asyncio.sleep(0.1)
                
            # 이미 매칭 중인지 확인
            if await self.service._has_active_match():
                logger.warning(f"User {self.user_id} tried to connect but already has an active match")
                await self.close()
                return

            # 채널 그룹에 추가 후 accept
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()

            # 사용자 온라인 상태 표시
            await self.service.mark_user_online()

            logger.info(f"User {self.user.id} connected to match service")

        except Exception as e:
            logger.error(f"Error connecting user {self.user.id}: {e}")
            try:
                await self.channel_layer.group_discard(self.group_name, self.channel_name)
            except Exception as ex:
                logger.warning(f"Failed to discard group for user {self.user.id}: {ex}")
            await self.close()

    async def disconnect(self, close_code):
        """연결 해제 시 정리"""
        try:
            affected_users = await self.service.handle_disconnect_cleanup()
            
            logger.info(f"User {self.user.id} disconnected, affected users: {affected_users}")
            
            for user_id in affected_users:
                if user_id != self.user.id:
                    await self.channel_layer.group_send(
                        f"user_{user_id}",
                        {
                            "type": "match_cancelled",
                            "from": self.user.username
                        }
                    )

            room_name = getattr(self, "current_room_name", None)
            if room_name:
                await self.channel_layer.group_send(
                    f"voicechat_{room_name}",
                    {
                        "type": "force_disconnect",
                        "reason": "match_disconnected"
                    }
                )
            
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            
        except Exception as e:
            logger.error(f"Error during disconnect cleanup for user {self.user.id}: {e}")

    async def receive(self, text_data):
        """메시지 수신 처리"""
        try:
            data = json.loads(text_data)
            action = data.get("action")

            if action == "join_queue":
                await self.handle_join_queue()
            elif action == "respond":
                await self.handle_response(data)
            elif action == "leave_queue":
                await self.handle_leave_queue()
            else:
                logger.warning(f"Unknown action '{action}' from user {self.user.id}")
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from user {self.user.id}: {text_data}")
        except Exception as e:
            logger.error(f"Error processing message from user {self.user.id}: {e}")

    async def handle_join_queue(self):
        """큐 참가 처리"""
        try:
            success = await self.service.add_to_queue()
            if success:
                await self.try_match()
        except Exception as e:
            logger.error(f"Error joining queue for user {self.user.id}: {e}")

    async def handle_leave_queue(self):
        """큐 떠나기 처리"""
        try:
            await self.service.remove_from_queue()
        except Exception as e:
            logger.error(f"Error leaving queue for user {self.user.id}: {e}")

    async def try_match(self):
        """매칭 시도 - 단순화된 원자적 매칭 시스템"""
        try:
            result, matched_user = await self.service.find_and_match_atomic()
            
            if result in ["no_wallet", "not_enough_gems"]:
                await self.send_json({
                    "type": "gem_error",
                    "reason": result
                })
                logger.warning(f"User {self.user.id} gem deduction failed: {result}")
                return

            if result == "match_created" and matched_user:
                image_url = self.user.profile_image.url if self.user.profile_image else ""
                matched_user_image_url = matched_user.profile_image.url if matched_user.profile_image else ""

                host = settings.SERVER_HOST
                absolute_url = host + image_url

                await self.send_json({
                    "type": "match_found",
                    "partner": matched_user.username,
                    "partner_image_url": host + matched_user_image_url,
                    "partner_age": matched_user.age,
                    "partner_gender": matched_user.gender,
                })

                await self.channel_layer.group_send(
                    f"user_{matched_user.id}",
                    {
                        "type": "notify_match",
                        "partner": self.user.username,
                        "partner_image_url": absolute_url,
                        "partner_age": self.user.age if self.user.age else 0,
                        "partner_gender": self.user.gender if self.user.gender else "unknown",
                    }
                )
                
                logger.info(f"Match created between {self.user.id} and {matched_user.id}")
                return

            elif result in ["no_setting", "no_match", "already_matched"]:
                logger.debug(f"Match result for user {self.user.id}: {result}")
                return

            elif result == "matching_in_progress":
                logger.debug(f"Global matching in progress, retrying for user {self.user.id}")
                await asyncio.sleep(0.1)
                if await self.service.is_user_online():
                    await self.service.add_to_queue()
                return

            else:
                logger.error(f"Match error for user {self.user.id}: {result}")
                return
        except Exception as e:
            logger.error(f"Exception during match attempt for user {self.user.id}: {e}")

    async def handle_response(self, data):
        """매치 응답 처리"""
        try:
            partner_name = data.get("partner")
            response = data.get("response")  # accept/reject

            if not partner_name or not response:
                logger.warning(f"User {self.user.id} sent invalid response data: {data}")
                return

            current_matches = await self.service.get_current_match_requests()
            if not current_matches:
                await self.send_json({"type": "match_cancelled", "reason": "no_active_match"})
                return

            target_match = None
            for match_data in current_matches:
                if match_data['user1_name'] == partner_name or match_data['user2_name'] == partner_name:
                    target_match = match_data
                    break

            if not target_match:
                logger.info(f"User {self.user.id} no match found with partner {partner_name}")
                return

            result, other_user = await self.service.update_match_status_and_create_room(target_match, response)

            await self.send_json({
                "type": "match_response",
                "result": response,
                "from": self.user.username
            })

            other_user_id = target_match['user2'] if target_match['user1'] == self.user_id else target_match['user1']

            if result == "success":
                room_name = f"{min(self.user.id, other_user.id)}_{max(self.user.id, other_user.id)}"
                self.current_room_name = room_name

                await self.send_json({
                    "type": "match_success",
                    "room": room_name
                })

                await self.channel_layer.group_send(
                    f"user_{other_user.id}",
                    {
                        "type": "match_success_notification",
                        "room": room_name
                    }
                )
            elif result == "partner_offline":
                await self.send_json({
                    "type": "match_cancelled",
                    "from": partner_name
                })
            elif result in ["accept", "rejected"]:
                await self.channel_layer.group_send(
                    f"user_{other_user_id}",
                    {
                        "type": "match_response",
                        "result": response,
                        "from": other_user_id
                    }
                )

        except Exception as e:
            logger.error(f"Error handling response from user {self.user.id}: {e}")

    async def force_disconnect(self, event):
        reason = event.get("reason", "unknown")
        logger.info(f"Force disconnecting due to: {reason}")
        await self.close()

    async def match_cancelled(self, event):
        await self.send_json({
            "type": "match_cancelled",
            "from": event.get("from")
        })

    async def notify_match(self, event):
        await self.send_json({
            "type": "match_found",
            "partner": event.get("partner", ""),
            "partner_image_url": event.get("partner_image_url", ""),
            "partner_age": event.get("partner_age", 0),
            "partner_gender": event.get("partner_gender", "unknown")
        })

    async def match_result_notification(self, event):
        await self.send_json({
            "type": "match_response",
            "result": event["result"],
            "from": event["from"]
        })

    async def match_success_notification(self, event):
        await self.send_json({
            "type": "match_success",
            "room": event["room"]
        })

    async def error_notification(self, event):
        pass  # 프론트엔드에서 사용하지 않음

    # 디버깅용 메서드
    async def send_to_partner(self, partner_id, message_type, data):
        try:
            await self.channel_layer.group_send(
                f"user_{partner_id}",
                {
                    "type": message_type,
                    **data
                }
            )
        except Exception as e:
            logger.error(f"Error sending to partner {partner_id}: {e}")

    async def get_queue_status(self):
        try:
            status = await self.service.get_queue_status()
            logger.info(f"Queue status for user {self.user.id}: {status}")
        except Exception as e:
            logger.error(f"Error getting queue status: {e}")
