from rest_framework.test import APITestCase, APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from match.models import MatchSetting, MatchRequest

User = get_user_model()

class MatchTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(username='user1', password='pass123', age=25, gender='male', is_matching=True)
        self.user2 = User.objects.create_user(username='user2', password='pass123', age=26, gender='female', is_matching=True)
        self.user3 = User.objects.create_user(username='user3', password='pass123', age=24, gender='female', is_matching=False)  # 매칭 중 아님

        # JWT 토큰 발급 및 인증 설정
        refresh = RefreshToken.for_user(self.user1)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')

    def test_01_save_match_setting(self):
        url = '/api/match/settings/'
        data = {
            'preferred_gender': 'female',
            'age_range': [20, 30],
            'radius_km': 10
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['message'], '매칭 조건이 저장되었습니다.')

        setting = MatchSetting.objects.get(user=self.user1)
        self.assertEqual(setting.age_range_min, 20)
        self.assertEqual(setting.age_range_max, 30)
        self.assertEqual(setting.preferred_gender, 'female')

    def test_02_random_matching_success(self):
        MatchSetting.objects.create(
            user=self.user1,
            preferred_gender='female',
            age_range_min=20,
            age_range_max=30,
            radius_km=10
        )

        # user2와 user3 중 user2만 is_matching=True이므로 후보자는 user2뿐임
        url = '/api/match/random/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('matched_user', response.data)
        self.assertIn('show_time_sec', response.data)
        self.assertIn('match_id', response.data)

    def test_03_random_matching_no_candidate(self):
        MatchSetting.objects.create(
            user=self.user1,
            preferred_gender='male',
            age_range_min=20,
            age_range_max=30,
            radius_km=10
        )

        # user2, user3 모두 매칭 중 아님으로 설정
        User.objects.exclude(id=self.user1.id).update(is_matching=False)

        url = '/api/match/random/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data['message'], '조건에 맞는 유저가 없습니다.')

    def test_04_match_decision_accept(self):
        MatchSetting.objects.create(
            user=self.user1,
            preferred_gender='female',
            age_range_min=20,
            age_range_max=30,
            radius_km=10
        )
        match_request = MatchRequest.objects.create(
            requester=self.user1,
            matched_user=self.user2,
            status='pending'
        )

        url = '/api/match/decision/'
        data = {
            'match_id': match_request.id,
            'decision': 'accept'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'matched')

        match_request.refresh_from_db()
        self.assertEqual(match_request.status, 'accepted')

    def test_05_match_decision_reject(self):
        match_request = MatchRequest.objects.create(
            requester=self.user1,
            matched_user=self.user2,
            status='pending'
        )

        url = '/api/match/decision/'
        data = {
            'match_id': match_request.id,
            'decision': 'reject'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'next')

        match_request.refresh_from_db()
        self.assertEqual(match_request.status, 'rejected')
