# users/tests/test_views.py
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from accounts.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from io import BytesIO
from PIL import Image

class UserProfileViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            age=25,
            gender="male"
        )
        self.url = reverse("user-profile")
        self.token = str(RefreshToken.for_user(self.user).access_token)
        self.auth_header = {'HTTP_AUTHORIZATION': f'Bearer {self.token}'}

    def test_profile_retrieve(self):
        response = self.client.get(self.url, **self.auth_header)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], self.user.username)
        self.assertEqual(response.data['age'], self.user.age)
        self.assertEqual(response.data['gender'], self.user.gender)

    def generate_test_image(self):
        file = BytesIO()
        image = Image.new("RGB", (100, 100), "blue")
        image.save(file, "jpeg")
        file.name = "test.jpg"
        file.seek(0)
        return file

    def test_profile_update(self):
        new_username = "updateduser"
        image = self.generate_test_image()

        data = {
            "username": new_username,
            "profile_image": image
        }

        response = self.client.put(self.url, data, format='multipart', **self.auth_header)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, new_username)
        self.assertTrue(self.user.profile_image.name.endswith("test.jpg"))
