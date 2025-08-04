import pytest
from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.test import override_settings
from tori_backend.routing import application
from match.models import MatchQueue

User = get_user_model()

@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestMatchConsumer:

    @database_sync_to_async
    def create_user(self, username):
        return User.objects.create_user(username=username, password="testpass123")

    @override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
    async def test_connect_and_enter_queue(self):
        user = await self.create_user("testuser")

        communicator = WebsocketCommunicator(application, "/ws/match/")
        communicator.scope['user'] = user

        connected, _ = await communicator.connect()
        assert connected

        queue = await database_sync_to_async(MatchQueue.objects.get)(user=user)
        assert queue.is_active is True

        await communicator.disconnect()

    @override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
    async def test_heartbeat_message(self):
        user = await self.create_user("heartbeatuser")

        communicator = WebsocketCommunicator(application, "/ws/match/")
        communicator.scope['user'] = user

        connected, _ = await communicator.connect()
        assert connected

        await communicator.send_json_to({"action": "heartbeat"})

        await communicator.disconnect()
