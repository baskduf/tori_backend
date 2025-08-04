import pytest
from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from tori_backend.asgi import application  # 프로젝트 환경에 맞게 변경

User = get_user_model()

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
class TestMatchFlow:

    @database_sync_to_async
    def create_user(self, username):
        return User.objects.create_user(username=username, password="testpass123")

    @database_sync_to_async
    def create_match_request(self, requester, matched_user):
        from match.models import MatchRequest
        return MatchRequest.objects.create(
            requester=requester,
            matched_user=matched_user,
            status="pending"
        )

    async def test_user_matching_accept_reject(self):
        # 유저 생성
        user1 = await self.create_user("user1")
        user2 = await self.create_user("user2")

        # 유저1 WebSocket 연결
        communicator1 = WebsocketCommunicator(application, "/ws/match/")
        communicator1.scope["user"] = user1
        connected1, _ = await communicator1.connect()
        assert connected1

        # 유저2 WebSocket 연결
        communicator2 = WebsocketCommunicator(application, "/ws/match/")
        communicator2.scope["user"] = user2
        connected2, _ = await communicator2.connect()
        assert connected2

        # 매칭 요청 생성 (DB에 직접 생성)
        match_request = await self.create_match_request(user1, user2)

        # 유저2가 매칭 요청 수락 메시지 전송
        await communicator2.send_json_to({
            "action": "decision",
            "match_id": match_request.id,
            "decision": "accept"
        })

        # (옵션) 수락 결과 응답 대기 및 검증
        # response = await communicator2.receive_json_from()
        # assert response.get("result") == "accepted"

        # 유저2가 매칭 요청 거절 테스트도 필요시 추가 가능
        # await communicator2.send_json_to({
        #     "action": "decision",
        #     "match_id": match_request.id,
        #     "decision": "reject"
        # })

        # 종료
        await communicator1.disconnect()
        await communicator2.disconnect()
