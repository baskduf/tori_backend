from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import UserGemWallet, GemTransaction, PurchaseReceipt
from .serializers import WalletSerializer, TransactionSerializer, PurchaseReceiptSerializer
from .services import add_gems, spend_gems

from django.db import transaction
from rest_framework import status

class WalletView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        wallet, _ = UserGemWallet.objects.get_or_create(user=request.user)
        serializer = WalletSerializer(wallet)
        return Response(serializer.data)


class TransactionListView(generics.ListAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return GemTransaction.objects.filter(user=self.request.user).order_by("-created_at")


class PurchaseConfirmView(APIView):
    """
    앱에서 Google purchaseToken을 전송하면 서버 검증 후 gem 충전
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        purchase_token = request.data.get("purchase_token")
        product_id = request.data.get("product_id")
        order_id = request.data.get("order_id")

        # TODO: Google Play Developer API 호출해 purchase_token 검증해야 함
        # 현재는 Mock 처리
        receipt, created = PurchaseReceipt.objects.get_or_create(
            purchase_token=purchase_token,
            defaults={
                "user": request.user,
                "product_id": product_id,
                "order_id": order_id,
                "acknowledged": True
            }
        )

        if not created:
            return Response({"detail": "이미 처리된 결제입니다."}, status=400)

        # 예시: product_id → gem 개수 매핑
        gem_amount = 100 if product_id == "gem_pack_100" else 0
        wallet = add_gems(request.user, gem_amount, note=f"Purchase {product_id}")

        return Response({
            "wallet": WalletSerializer(wallet).data,
            "receipt": PurchaseReceiptSerializer(receipt).data
        })


class RewardedAdView(APIView):
    @transaction.atomic
    def post(self, request):
        user = request.user
        reward_amount = request.data.get("reward_amount")
        ad_unit_id = request.data.get("ad_unit_id")

        if not reward_amount or not ad_unit_id:
            return Response({"error": "Reward amount and ad_unit_id are required"}, status=status.HTTP_400_BAD_REQUEST)

        # 이미 지급된 광고인지 확인
        if GemTransaction.objects.filter(user=user, ad_unit_id=ad_unit_id, transaction_type="reward").exists():
            return Response({"error": "Reward already granted for this ad"}, status=status.HTTP_400_BAD_REQUEST)

        # 지갑 업데이트
        wallet, _ = UserGemWallet.objects.get_or_create(user=user)
        wallet.balance += int(reward_amount)
        wallet.save()

        # 트랜잭션 기록
        GemTransaction.objects.create(
            user=user,
            transaction_type="reward",
            amount=int(reward_amount),
            ad_unit_id=ad_unit_id,
            note="Reward from watched ad"
        )
        return Response({ "message": "Reward granted",
            "new_balance": wallet.balance
        }, status=status.HTTP_200_OK)
    