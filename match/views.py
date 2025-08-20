# match/views.py
from rest_framework import generics, permissions
from .models import MatchSetting
from .serializers import MatchSettingSerializer  # ✅ 필요한 serializer import

class MatchSettingView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = MatchSettingSerializer  # ✅ 이 줄 추가

    def get_object(self):
        obj, created = MatchSetting.objects.get_or_create(
            user=self.request.user,
            defaults={
                'preferred_gender': 'any',
                'age_min': 18,
                'age_max': 99,
                'radius_km': 10,
            }
        )
        return obj
    
    def get_queryset(self):
        return MatchSetting.objects.filter(user=self.request.user)
