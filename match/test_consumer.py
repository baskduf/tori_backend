import pytest
import json
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import override_settings
from asgiref.sync import sync_to_async
from rest_framework_simplejwt.tokens import RefreshToken
from tori_backend.asgi import application  # asgi 경로에 맞게 수정
from match.models import MatchSetting, MatchedRoom

User = get_user_model()

@sync_to_async
def create_user(username, password, gender, age):
    return User.objects.create_user(username=username, password=password, gender=gender, age=age)

@sync_to_async
def create_match_setting(user, age_min, age_max, preferred_gender):
    return MatchSetting.objects.create(user=user, age_min=age_min, age_max=age_max, preferred_gender=preferred_gender)

@sync_to_async
def check_matched_room_exists(user1, user2):
    return MatchedRoom.objects.filter(user1=user1, user2=user2).exists()

@sync_to_async
def get_token_for_user(user):
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token)

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
async def test_match_consumer_flow():
    user1 = await create_user("user1", "pass", "male", 25)
    user2 = await create_user("user2", "pass", "female", 23)

    await create_match_setting(user1, 20, 30, 'female')
    await create_match_setting(user2, 20, 30, 'male')

    token1 = await get_token_for_user(user1)
    token2 = await get_token_for_user(user2)

    communicator1 = WebsocketCommunicator(application, f"/ws/match/?token={token1}")
    connected1, _ = await communicator1.connect()
    assert connected1

    communicator2 = WebsocketCommunicator(application, f"/ws/match/?token={token2}")
    connected2, _ = await communicator2.connect()
    assert connected2

    # user1 큐 진입
    await communicator1.send_json_to({"action": "join_queue"})
    # user2 큐 진입
    await communicator2.send_json_to({"action": "join_queue"})

    # user1 매칭 발견 수신
    res1 = await communicator1.receive_json_from()
    assert res1["type"] == "match_found"
    assert res1["partner"] == "user2"

    # user2 매칭 발견 수신
    res2 = await communicator2.receive_json_from()
    assert res2["type"] == "match_found"
    assert res2["partner"] == "user1"

    # user1 수락
    await communicator1.send_json_to({"action": "respond", "partner": "user2", "response": "accept"})
    # user2 수락
    await communicator2.send_json_to({"action": "respond", "partner": "user1", "response": "accept"})

    # user1 수락 결과 수신
    res_accept1 = await communicator1.receive_json_from()
    assert res_accept1["type"] == "match_response"
    assert res_accept1["result"] == "accept"

    # user2 수락 결과 수신
    res_accept2 = await communicator2.receive_json_from()
    assert res_accept2["type"] == "match_response"
    assert res_accept2["result"] == "accept"

    matched = await check_matched_room_exists(user1, user2)
    assert matched

    await communicator1.disconnect()
    await communicator2.disconnect()
