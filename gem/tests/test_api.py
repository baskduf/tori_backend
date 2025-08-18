from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from gem.models import UserGemWallet, PurchaseReceipt

User = get_user_model()

class APITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="carol", password="pass1234", email="carol@test.com"
        )
        self.client = APIClient()

        # JWT 토큰 발급
        refresh = RefreshToken.for_user(self.user)
        access_token = str(refresh.access_token)

        # 인증 헤더 설정
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

    def test_wallet_get_initial(self):
        res = self.client.get("/api/gem/wallet/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["balance"], 0)

    def test_purchase_confirm_creates_receipt_and_adds_gems(self):
        payload = {
            "purchase_token": "tok-111",
            "product_id": "gem_pack_100",
            "order_id": "ORDER-XYZ",
        }
        res = self.client.post("/api/gem/purchase/confirm/", payload, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(PurchaseReceipt.objects.filter(purchase_token="tok-111").exists())

        wallet = UserGemWallet.objects.get(user=self.user)
        self.assertEqual(wallet.balance, 100)

    def test_purchase_confirm_idempotent(self):
        payload = {
            "purchase_token": "tok-dup",
            "product_id": "gem_pack_100",
            "order_id": "ORDER-1",
        }
        first = self.client.post("/api/gem/purchase/confirm/", payload, format="json")
        self.assertEqual(first.status_code, 200)

        second = self.client.post("/api/gem/purchase/confirm/", payload, format="json")
        self.assertEqual(second.status_code, 400)
        self.assertIn("이미 처리된 결제", second.data["detail"])

    def test_transactions_list(self):
        self.client.post("/api/gem/purchase/confirm/", {
            "purchase_token": "tok-tx",
            "product_id": "gem_pack_100",
            "order_id": "ORDER-TX",
        }, format="json")

        res = self.client.get("/api/gem/transactions/")
        self.assertEqual(res.status_code, 200)
        self.assertGreaterEqual(len(res.data), 1)
