from django.test import TestCase
from django.contrib.auth import get_user_model
from gem.models import UserGemWallet, GemTransaction, PurchaseReceipt

User = get_user_model()

class ModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="alice", password="pass1234", email="alice@test.com"
        )

    def test_wallet_created_and_str(self):
        wallet = UserGemWallet.objects.create(user=self.user, balance=10)
        self.assertEqual(wallet.balance, 10)
        self.assertIn("Wallet", str(wallet))

    def test_transaction_create_and_str(self):
        tx = GemTransaction.objects.create(
            user=self.user, transaction_type="purchase", amount=100, note="init"
        )
        self.assertEqual(tx.amount, 100)
        self.assertIn("purchase", str(tx))

    def test_receipt_unique_purchase_token(self):
        PurchaseReceipt.objects.create(
            user=self.user, order_id="ORDER-1", product_id="gem_pack_100",
            purchase_token="token-abc", acknowledged=True
        )
        with self.assertRaises(Exception):
            PurchaseReceipt.objects.create(
                user=self.user, order_id="ORDER-2", product_id="gem_pack_100",
                purchase_token="token-abc", acknowledged=True
            )
