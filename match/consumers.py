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
        self.heartbeat_task: asyncio.Task | None = None

        try:
            # 중복 로그인 체크
        # 기존 접속 확인
            if await self.service.is_user_online():
                logger.info(f"User {self.user_id} is already online, disconnecting old session")

                # 기존 세션에게 강제 종료 메시지 전송
                await self.channel_layer.group_send(
                    f"user_{self.user_id}",
                    {
                        "type": "force_disconnect",
                        "reason": "new_login"
                    }
                )

                # 기존 연결이 끊길 시간 확보
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

            # 주기적 heartbeat task 실행
            self.heartbeat_task = asyncio.create_task(self.send_heartbeat())

            logger.info(f"User {self.user.id} connected to match service")

        except Exception as e:
            logger.error(f"Error connecting user {self.user.id}: {e}")
            # 예외 발생 시 그룹 제거 및 close 시도
            if self.heartbeat_task is not None:
                self.heartbeat_task.cancel()
                self.heartbeat_task = None
            try:
                await self.channel_layer.group_discard(self.group_name, self.channel_name)
            except Exception as ex:
                logger.warning(f"Failed to discard group for user {self.user.id}: {ex}")
            await self.close()


    async def disconnect(self, close_code):
        """연결 해제 시 정리"""
        try:
            # services의 handle_disconnect_cleanup 사용
            affected_users = await self.service.handle_disconnect_cleanup()
            
            logger.info(f"User {self.user.id} disconnected, affected users: {affected_users}")
            
            # 영향받은 사용자들에게 알림 (자신 제외)
            for user_id in affected_users:
                if user_id != self.user.id:
                    await self.channel_layer.group_send(
                        f"user_{user_id}",
                        {
                            "type": "match_cancelled",
                            "from": self.user.username
                        }
                    )

            # 여기서 signaling consumer 강제 종료
            room_name = getattr(self, "current_room_name", None)
            if room_name:
                await self.channel_layer.group_send(
                    f"voicechat_{room_name}",
                    {
                        "type": "force_disconnect",
                        "reason": "match_disconnected"
                    }
                )
            
            if self.heartbeat_task is not None:
                self.heartbeat_task.cancel()
                self.heartbeat_task = None

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
                    # 프론트엔드 호환: queue_joined 응답 없이 즉시 매칭 시도
                    await self.try_match()
                # 실패시에도 에러 응답 없음 (기존 동작과 동일)
                
        except Exception as e:
            logger.error(f"Error joining queue for user {self.user.id}: {e}")
            # 프론트엔드 호환: 에러 응답 없음

    async def handle_leave_queue(self):
        """큐 떠나기 처리"""
        try:
            success = await self.service.remove_from_queue()
            # 프론트엔드 호환: 응답 없음 (조용히 처리)
        except Exception as e:
            logger.error(f"Error leaving queue for user {self.user.id}: {e}")

    async def try_match(self):
        """매칭 시도 - 단순화된 원자적 매칭 시스템"""
        try:
            # 원자적 매칭 실행
            result, matched_user = await self.service.find_and_match_atomic()
            # 2. 보석 관련 처리
            if result in ["no_wallet", "not_enough_gems"]:
                await self.send_json({
                    "type": "gem_error",
                    "reason": result  # "no_wallet" 또는 "not_enough_gems"
                })
                logger.warning(f"User {self.user.id} gem deduction failed: {result}")
                return
            
            
            if result == "match_created" and matched_user:

                image_url = self.user.profile_image.url  # 예: /media/profile_images/web_image_wpR7tL6.png
                matched_user_image_url = matched_user.profile_image.url

                # 실제로는 호스트까지 붙여야 함
                host = settings.SERVER_HOST  # 서버주소, 개발용이라면 localhost

                absolute_url = host + image_url

                await self.send_json({
                    "type": "match_found",
                    "partner": matched_user.username,
                    "partner_image_url": host + matched_user_image_url if matched_user.profile_image else '',
                    "partner_age": matched_user.age,
                    "partner_gender": matched_user.gender,
                })


                # 상대방에게 매치 발견 알림
                await self.channel_layer.group_send(
                    f"user_{matched_user.id}",
                    {
                        "type": "notify_match",
                        "partner": self.user.username,
                        "partner_image_url": absolute_url if self.user.profile_image else '',
                        "partner_age": self.user.age if self.user.age is not None else 0,
                        "partner_gender": self.user.gender if self.user.gender else 'unknown',
                    }
                )
                
                logger.info(f"Match created between {self.user.id} and {matched_user.id}")
                
            elif result == "no_setting":
                # 설정이 없는 경우
                logger.warning(f"User {self.user.id} has no match settings")
                return
                
            elif result == "no_match":
                # 적합한 상대방이 없음 - 조용히 대기
                logger.debug(f"No eligible match found for user {self.user.id}")
                return
                
            elif result == "already_matched":
                # 이미 매칭 중인 상태
                logger.debug(f"User {self.user.id} already has active match")
                return
                
            elif result == "matching_in_progress":
                # 다른 매칭이 진행 중 - 짧은 지연 후 재시도
                logger.debug(f"Global matching in progress, retrying for user {self.user.id}")
                await asyncio.sleep(0.1)  # 100ms 대기
                if await self.service.is_user_online():
                    await self.service.add_to_queue()
                return
                
            else:  # "error" 또는 기타
                # 일반적인 오류 - 로그만 남기고 조용히 처리
                logger.error(f"Match error for user {self.user.id}: {result}")
                return
                    
        except Exception as e:
            logger.error(f"Exception during match attempt for user {self.user.id}: {e}")
            # 예외 발생 시에도 조용히 처리

    async def handle_response(self, data):
        """매치 응답 처리 - 프론트엔드 호환"""
        try:
            partner_name = data.get("partner")
            response = data.get("response")  # accept 또는 reject

            logger.info(f"User {self.user.id} handle_response called with partner: {partner_name}, response: {response}")

            if not partner_name or not response:
                logger.warning(f"User {self.user.id} sent invalid response data: {data}")
                # 프론트엔드 호환: 에러 응답 없음
                return

            # 현재 매치 요청들 조회
            current_matches = await self.service.get_current_match_requests()
            logger.debug(f"User {self.user.id} current_matches: {current_matches}")
            if not current_matches:
                logger.info(f"User {self.user.id} has no current matches")
                await self.send_json({"type": "match_cancelled", "reason": "no_active_match"})
                return

            # 해당 파트너와의 매치 찾기
            target_match = None
            for match_data in current_matches:
                if (match_data['user1_name'] == partner_name or 
                    match_data['user2_name'] == partner_name):
                    target_match = match_data
                    break

            if not target_match:
                logger.info(f"User {self.user.id} no match found with partner {partner_name}")
                # 프론트엔드 호환: 에러 응답 없음
                return

            logger.info(f"User {self.user.id} found target match: {target_match}")

            # 매치 상태 업데이트 및 방 생성
            result, other_user = await self.service.update_match_status_and_create_room(
                target_match, response
            )
            logger.info(f"User {self.user.id} update_match_status result: {result}, other_user: {getattr(other_user, 'id', None)}")

            # 본인에게 응답 결과 전송 (프론트엔드 호환)
            await self.send_json({
                "type": "match_response",
                "result": response,  # accept/reject 그대로
                "from": self.user.username
            })

            # 상대방 정보 조회
            other_user_id = (target_match['user2'] if target_match['user1'] == self.user_id 
                 else target_match['user1'])
            logger.info(f"################{result}##################")

            # 결과에 따른 처리
            if result == "success":
                # 양방향 수락 완료 - 방 생성됨
                room_name = f"{min(self.user.id, other_user.id)}_{max(self.user.id, other_user.id)}"
                self.current_room_name = room_name
                logger.info(f"User {self.user.id} successful match, room: {room_name}")

                # 본인에게 성공 알림 (프론트엔드 호환)
                await self.send_json({
                    "type": "match_success",
                    "room": room_name
                })
                
                # 상대방에게도 성공 알림 (프론트엔드 호환)
                await self.channel_layer.group_send(
                    f"user_{other_user.id}",
                    {
                        "type": "match_success_notification",
                        "room": room_name
                    }
                )
                
            elif result == "partner_offline":
                logger.info(f"User {self.user.id} partner offline: {partner_name}")
                # 상대방 오프라인 - 매치 취소로 처리 (프론트엔드 호환)
                await self.send_json({
                    "type": "match_cancelled",
                    "from": partner_name
                })
                
                
            elif result in ["accept", "rejected"]:
                logger.info(f"User {self.user.id} notified partner {other_user_id} with response {response}")
                # 상대방에게 응답 알림 (실제 응답값 사용)
                await self.channel_layer.group_send(
                    f"user_{other_user_id}",
                    {
                        "type": "match_response",
                        "result": response,  # 실제 응답값 사용
                        "from": other_user_id
                    }
                )
            # 기타 에러 상황은 조용히 처리 (프론트엔드 호환)
                
        except Exception as e:
            logger.error(f"Error handling response from user {self.user.id}: {e}")
            # 프론트엔드 호환: 에러 응답 없음

    async def match_response(self, event):
        await self.send_json({
            "type": "match_response",
            "result": event["result"],
            "from": event["from"]
        })

    async def force_disconnect(self, event):
        reason = event.get("reason", "unknown")
        logger.info(f"Force disconnecting due to: {reason}")
        await self.close()

    
    # WebSocket 이벤트 핸들러들 - 프론트엔드 호환
    async def match_cancelled(self, event):
        """매치 취소 알림 - 프론트엔드 호환"""
        await self.send_json({
            "type": "match_cancelled",
            "from": event.get("from")
        })

    async def notify_match(self, event):
        """매치 발견 알림 - 프론트엔드 호환"""
        await self.send_json({
            "type": "match_found",
            "partner": event.get("partner", ""),
            "partner_image_url": event.get("partner_image_url", ""),  # 이미지 URL
            "partner_age": event.get("partner_age", 0),              # 나이
            "partner_gender": event.get("partner_gender", "unknown") # 성별
        })


    async def match_result_notification(self, event):
        """매치 응답 결과 알림 - 프론트엔드 호환"""
        await self.send_json({
            "type": "match_response",
            "result": event["result"],  # accept/reject
            "from": event["from"]
        })

    async def match_success_notification(self, event):
        """매치 성공 알림 - 프론트엔드 호환"""
        await self.send_json({
            "type": "match_success",
            "room": event["room"]
        })

    async def error_notification(self, event):
        """에러 알림 - 프론트엔드에서 사용하지 않으므로 제거"""
        pass

    # 디버깅/관리자용 메서드들 (프론트엔드 호환하지 않음)
    async def send_to_partner(self, partner_id, message_type, data):
        """파트너에게 메시지 전송"""
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
        """큐 상태 조회 (디버깅용) - 프론트엔드 호환하지 않음"""
        try:
            status = await self.service.get_queue_status()
            # 디버깅용으로만 로그에 출력
            logger.info(f"Queue status for user {self.user.id}: {status}")
        except Exception as e:
            logger.error(f"Error getting queue status: {e}")

    async def send_heartbeat(self):
        try:
            while True:
                await asyncio.sleep(5)  # 5초마다 하트비트
                try:
                    ok = await self.service.mark_user_online()
                    if not ok:  # 반환값이 False면 실패 처리
                        logger.warning(f"Heartbeat failed for user {self.user.id}, disconnecting...")
                        await self.close()
                        break
                except Exception as e:
                    logger.error(f"Heartbeat error for user {self.user.id}: {e}")
                    await self.close()
                    break
        except asyncio.CancelledError:
            pass
