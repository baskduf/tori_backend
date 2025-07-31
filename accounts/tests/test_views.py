from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()

class AuthViewTests(APITestCase):
    def setUp(self):
        self.signup_url = reverse('signup')
        self.login_url = reverse('token_obtain_pair')
        self.logout_url = reverse('logout')
        self.user_data = {
            "username": "testuser",
            "password": "Testpass123!",
            "password2": "Testpass123!",
            "age": 25,
            "gender": "male"
        }

    def test_signup(self):
        response = self.client.post(self.signup_url, self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_login(self):
        # 회원가입 먼저
        self.client.post(self.signup_url, self.user_data, format='json')
        login_data = {
            "username": "testuser",
            "password": "Testpass123!"
        }
        response = self.client.post(self.login_url, login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_logout(self):
        # 회원가입 + 로그인
        signup_resp = self.client.post(self.signup_url, self.user_data, format='json')
        refresh_token = signup_resp.data['refresh']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {signup_resp.data["access"]}')

        logout_resp = self.client.post(self.logout_url, {'refresh': refresh_token}, format='json')
        self.assertEqual(logout_resp.status_code, status.HTTP_205_RESET_CONTENT)
