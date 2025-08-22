from django.urls import path
from .views import WalletView, TransactionListView, PurchaseConfirmView, RewardedAdView

urlpatterns = [
    path("wallet/", WalletView.as_view(), name="wallet"),
    path("transactions/", TransactionListView.as_view(), name="transactions"),
    path("api/rewarded_ad/", RewardedAdView.as_view(), name="rewarded_ad"),
    path("purchase/confirm/", PurchaseConfirmView.as_view(), name="purchase_confirm"),
]
