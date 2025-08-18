from rest_framework import serializers
from .models import UserGemWallet, GemTransaction, PurchaseReceipt

class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserGemWallet
        fields = ["balance", "updated_at"]


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = GemTransaction
        fields = ["id", "transaction_type", "amount", "created_at", "note"]


class PurchaseReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseReceipt
        fields = ["id", "order_id", "product_id", "purchase_token", "acknowledged", "created_at"]
