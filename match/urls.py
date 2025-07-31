from django.urls import path
from .views import MatchSettingView, MatchRandomView, MatchDecisionView

urlpatterns = [
    path('settings/', MatchSettingView.as_view()),
    path('random/', MatchRandomView.as_view()),
    path('decision/', MatchDecisionView.as_view()),
]
