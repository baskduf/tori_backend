# match/urls.py
from django.urls import path
from .views import MatchSettingView

urlpatterns = [
    path('settings/', MatchSettingView.as_view(), name='match-setting'),
]
