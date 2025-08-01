# urls.py

from django.urls import path
from .views import (
    MatchSettingView,
    EnterMatchQueueView,
    MatchHeartbeatView,
    MatchRandomView,
    MatchCancelView,
    MatchDecisionView,
)

urlpatterns = [
    path('settings/', MatchSettingView.as_view(), name='match_settings'),
    path('enter_queue/', EnterMatchQueueView.as_view(), name='match_enter_queue'),
    path('heartbeat/', MatchHeartbeatView.as_view(), name='match_heartbeat'),
    path('random/', MatchRandomView.as_view(), name='match_random'),
    path('cancel/', MatchCancelView.as_view(), name='match_cancel'),
    path('decision/', MatchDecisionView.as_view(), name='match_decision'),
]
