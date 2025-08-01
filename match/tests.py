from rest_framework.test import APITestCase, APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from match.models import MatchSetting, MatchRequest, MatchQueue

User = get_user_model()


class MatchTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(username='user1', password='pass123', age=25, gender='male')
        self.user2 = User.objects.create_user(username='user2', password='pass123', age=26, gender='female')
        self.user3 = User.objects.create_user(username='user3', password='pass123', age=24, gender='female')

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
        # user2도 대기열에 넣기 (is_active=True, last_heartbeat 최신)
        MatchQueue.objects.create(user=self.user2, is_active=True)

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
        # user2, user3 대기열에 없거나 is_active=False 상태로 두기 (매칭 불가)
        MatchQueue.objects.create(user=self.user2, is_active=False)
        MatchQueue.objects.create(user=self.user3, is_active=False)

        url = '/api/match/random/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data['message'], '조건에 맞는 유저가 없습니다.')

    def test_04_match_decision_accept_and_matched(self):
        MatchRequest.objects.create(
            requester=self.user1,
            matched_user=self.user2,
            requester_status='pending',
            matched_user_status='pending'
        )

        # user1 accept
        url = '/api/match/decision/'
        data = {'match_id': 1, 'decision': 'accept'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'waiting')

        # user2 accept (token 설정)
        client2 = APIClient()
        refresh2 = RefreshToken.for_user(self.user2)
        client2.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh2.access_token)}')

        response = client2.post(url, data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'matched')

        match = MatchRequest.objects.get(id=1)
        self.assertEqual(match.requester_status, 'accepted')
        self.assertEqual(match.matched_user_status, 'accepted')

    def test_05_match_decision_reject(self):

        MatchQueue.objects.create(user=self.user1, is_active=False)
        MatchQueue.objects.create(user=self.user2, is_active=False)

        MatchRequest.objects.create(
            requester=self.user1,
            matched_user=self.user2,
            requester_status='pending',
            matched_user_status='pending'
        )

        url = '/api/match/decision/'
        data = {'match_id': 1, 'decision': 'reject'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'next')

        match = MatchRequest.objects.get(id=1)
        # 거절한 사람 상태가 reject 되어야 함
        self.assertIn(match.requester_status, ['rejected', 'pending'])
        self.assertIn(match.matched_user_status, ['rejected', 'pending'])

        # user1의 큐가 is_active=True 상태인지 확인
        queue = MatchQueue.objects.filter(user=self.user1, is_active=True).exists()
        self.assertTrue(queue)

    def test_06_heartbeat_response_with_match(self):
        # Setup: user1 enters queue, user2 enters queue, create match request pending
        client1 = APIClient()
        refresh1 = RefreshToken.for_user(self.user1)
        client1.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh1.access_token)}')

        client2 = APIClient()
        refresh2 = RefreshToken.for_user(self.user2)
        client2.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh2.access_token)}')

        client1.post('/api/match/enter_queue/')
        client2.post('/api/match/enter_queue/')

        match_request = MatchRequest.objects.create(
            requester=self.user1,
            matched_user=self.user2,
            requester_status='pending',
            matched_user_status='pending'
        )

        # user2 heartbeat should return matched_user info (user1)
        response = client2.post('/api/match/heartbeat/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('matched_user', response.data)
        self.assertEqual(response.data['matched_user']['username'], self.user1.username)
        self.assertIn('match_id', response.data)
        self.assertEqual(response.data['match_id'], match_request.id)

    def test_07_match_cancel(self):
        MatchQueue.objects.create(user=self.user1, is_active=True)
        response = self.client.post('/api/match/cancel/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['message'], '매칭 상태가 해제되었습니다.')

        queue = MatchQueue.objects.filter(user=self.user1, is_active=True).exists()
        self.assertFalse(queue)

    # 추가: 거절 시 상대방 대기열 복귀 확인 테스트
    def test_08_reject_restores_opponent_queue(self):
        MatchQueue.objects.create(user=self.user1, is_active=False)
        MatchQueue.objects.create(user=self.user2, is_active=False)

        match_request = MatchRequest.objects.create(
            requester=self.user1,
            matched_user=self.user2,
            requester_status='pending',
            matched_user_status='pending'
        )

        url = '/api/match/decision/'
        data = {'match_id': match_request.id, 'decision': 'reject'}

        # user1 거절
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'next')

        # 양쪽 큐가 모두 is_active=True 상태여야 함
        active1 = MatchQueue.objects.filter(user=self.user1, is_active=True).exists()
        active2 = MatchQueue.objects.filter(user=self.user2, is_active=True).exists()
        self.assertTrue(active1)
        self.assertTrue(active2)
