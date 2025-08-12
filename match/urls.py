# match/urls.py
from django.urls import path
from .views import MatchSettingView

urlpatterns = [
    path('', MatchSettingView.as_view(), name='match-setting'),
]
