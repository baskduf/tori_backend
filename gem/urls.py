from django.urls import path
from .views import WalletView, TransactionListView, PurchaseConfirmView

urlpatterns = [
    path("wallet/", WalletView.as_view(), name="wallet"),
    path("transactions/", TransactionListView.as_view(), name="transactions"),
    path("purchase/confirm/", PurchaseConfirmView.as_view(), name="purchase_confirm"),
]
