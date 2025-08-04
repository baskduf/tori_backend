# match/views.py
from rest_framework import generics, permissions
from .models import MatchSetting
from .serializers import MatchSettingSerializer

class MatchSettingView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        # 로그인한 유저의 세팅 객체가 없으면 새로 생성해서 반환
        obj, created = MatchSetting.objects.get_or_create(user=self.request.user,
                                                          defaults={
                                                              'preferred_gender': 'all',
                                                              'age_range_min': 18,
                                                              'age_range_max': 99,
                                                              'radius_km': 10,
                                                          })
        return obj
