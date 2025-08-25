# services.py
from asgiref.sync import sync_to_async
from django.db import transaction
from .models import UserGemWallet, GemTransaction

async def add_gems(user, amount, note=None):
    """
    지갑에 gems를 증가시키고 트랜잭션 기록
    """
    @transaction.atomic
    def increase():
        wallet, _ = UserGemWallet.objects.get_or_create(user=user)
        wallet.balance += int(amount)
        wallet.save(update_fields=["balance", "updated_at"])

        GemTransaction.objects.create(
            user=user,
            transaction_type="purchase",
            amount=int(amount),
            note=note or "Added gems"
        )
        return wallet.balance

    new_balance = await sync_to_async(increase)()
    return new_balance


async def spend_gems(user, amount, note=None):
    """
    지갑에서 gems를 감소시키고 트랜잭션 기록
    """
    @transaction.atomic
    def deduct():
        wallet, _ = UserGemWallet.objects.get_or_create(user=user)
        wallet.refresh_from_db()
        if wallet.balance < amount:
            raise ValueError("Not enough gems")
        wallet.balance -= int(amount)
        wallet.save(update_fields=["balance", "updated_at"])

        GemTransaction.objects.create(
            user=user,
            transaction_type="spend",
            amount=int(amount),
            note=note or "Spent gems"
        )
        return wallet.balance

    new_balance = await sync_to_async(deduct)()
    return new_balance


async def reward_gems(user, amount, ad_unit_id=None, note=None):
    """
    보상 형태로 gems 지급
    """
    @transaction.atomic
    def reward():
        wallet, _ = UserGemWallet.objects.get_or_create(user=user)
        wallet.balance += int(amount)
        wallet.save(update_fields=["balance", "updated_at"])

        GemTransaction.objects.create(
            user=user,
            transaction_type="reward",
            amount=int(amount),
            ad_unit_id=ad_unit_id,
            note=note or "Rewarded gems"
        )
        return wallet.balance

    new_balance = await sync_to_async(reward)()
    return new_balance
