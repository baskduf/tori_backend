import pytest
import asyncio
from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from tori_backend.asgi import application

User = get_user_model()

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
class TestMatchFlow:

    @database_sync_to_async
    def create_user(self, username):
        return User.objects.create_user(username=username, password="testpass123")

    async def connect_user(self, user):
        communicator = WebsocketCommunicator(application, "/ws/match/")
        communicator.scope["user"] = user
        connected, _ = await communicator.connect()
        assert connected
        return communicator

    @database_sync_to_async
    def get_match_request(self, requester, matched_user):
        from match.models import MatchRequest
        return MatchRequest.objects.filter(requester=requester, matched_user=matched_user).first()

    @database_sync_to_async
    def get_match_queue(self, user):
        from match.models import MatchQueue
        return MatchQueue.objects.filter(user=user).first()

    async def test_full_match_flow(self):
        # 1. 유저 생성
        user1 = await self.create_user("user1")
        user2 = await self.create_user("user2")

        # 2. WebSocket 연결
        comm1 = await self.connect_user(user1)
        comm2 = await self.connect_user(user2)

        # 3. 큐에 입장 (매칭 시작)
        await comm1.send_json_to({"action": "enter_queue"})
        await comm2.send_json_to({"action": "enter_queue"})

        # 4. 하트비트 보내기 (옵션)
        await comm1.send_json_to({"action": "heartbeat"})
        await comm2.send_json_to({"action": "heartbeat"})

        # 5. 매칭 발견 메시지 대기
        msg1 = await comm1.receive_json_from()
        msg2 = await comm2.receive_json_from()

        assert msg1["action"] == "match_found"
        assert msg2["action"] == "match_found"

        match_id = msg1["match_id"]

        # 6. 매칭 수락 (user2가 수락)
        await comm2.send_json_to({
            "action": "decision",
            "match_id": match_id,
            "decision": "accept"
        })

        # 7. 상태 변경 처리 대기 (consumer가 DB 업데이트 할 시간 부여)
        await asyncio.sleep(0.1)

        # 8. DB에서 상태 확인
        match_req = await self.get_match_request(user1, user2)
        assert match_req.status == "accepted"

        # 9. (옵션) 매칭 거절 시나리오 추가 가능
        # 예: 새 매칭 요청 생성 후 reject 테스트

        # 10. 퇴장 처리 (consumer에 exit_queue action 구현되어 있으면)
        # await comm1.send_json_to({"action": "exit_queue"})
        # await comm2.send_json_to({"action": "exit_queue"})

        # queue1 = await self.get_match_queue(user1)
        # queue2 = await self.get_match_queue(user2)
        # assert queue1.is_active is False
        # assert queue2.is_active is False

        # 11. 연결 종료
        await comm1.disconnect()
        await comm2.disconnect()
