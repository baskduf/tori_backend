from django.test import TestCase
from django.contrib.auth import get_user_model
from gem.models import UserGemWallet
from gem.services import add_gems, spend_gems

User = get_user_model()

class ServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="bob", password="pass1234", email="bob@test.com"
        )

    def test_add_gems(self):
        wallet = add_gems(self.user, 150, note="test add")
        self.assertEqual(wallet.balance, 150)

    def test_spend_gems_success(self):
        add_gems(self.user, 100)
        wallet = spend_gems(self.user, 60, note="test spend")
        self.assertEqual(wallet.balance, 40)

    def test_spend_gems_not_enough(self):
        add_gems(self.user, 30)
        with self.assertRaises(ValueError):
            spend_gems(self.user, 50)
        wallet = UserGemWallet.objects.get(user=self.user)
        self.assertEqual(wallet.balance, 30)
