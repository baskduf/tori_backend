from django.db import models
from django.conf import settings

class UserGemWallet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wallet")
    balance = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} Wallet ({self.balance} gems)"


class GemTransaction(models.Model):
    TRANSACTION_TYPES = [
        ("purchase", "Purchase"),
        ("spend", "Spend"),
        ("refund", "Refund"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="gem_transactions")
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True)

    def __str__(self):
        return f"{self.user.username} {self.transaction_type} {self.amount} gems"


class PurchaseReceipt(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="purchase_receipts")
    order_id = models.CharField(max_length=200, unique=True)
    product_id = models.CharField(max_length=200)
    purchase_token = models.CharField(max_length=500, unique=True)
    acknowledged = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Receipt {self.order_id} ({self.user.username})"
