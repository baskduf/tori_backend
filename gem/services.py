from django.db import transaction
from .models import UserGemWallet, GemTransaction, PurchaseReceipt

def add_gems(user, amount, note=""):
    """유저 지갑에 gem 충전"""
    with transaction.atomic():
        wallet, _ = UserGemWallet.objects.get_or_create(user=user)
        wallet.balance += amount
        wallet.save()

        GemTransaction.objects.create(
            user=user,
            transaction_type="purchase",
            amount=amount,
            note=note
        )
    return wallet


def spend_gems(user, amount, note=""):
    """유저가 gem 소비"""
    with transaction.atomic():
        wallet, _ = UserGemWallet.objects.get_or_create(user=user)
        if wallet.balance < amount:
            raise ValueError("Not enough gems")

        wallet.balance -= amount
        wallet.save()

        GemTransaction.objects.create(
            user=user,
            transaction_type="spend",
            amount=amount,
            note=note
        )
    return wallet
