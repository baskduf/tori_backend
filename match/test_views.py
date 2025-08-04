# match/tests.py
import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
def test_match_setting_api():
    user = User.objects.create_user(username="tester", password="testpass123")
    client = APIClient()
    client.login(username="tester", password="testpass123")

    # GET: 기본 세팅 조회 (없으면 생성)
    response = client.get("/api/match/settings/")
    assert response.status_code == 200
    assert response.data["preferred_gender"] == "all"

    # PUT: 세팅 변경
    response = client.put("/api/match/settings/", {
        "preferred_gender": "male",
        "age_range_min": 20,
        "age_range_max": 30,
        "radius_km": 5
    }, format='json')
    assert response.status_code == 200
    assert response.data["preferred_gender"] == "male"
