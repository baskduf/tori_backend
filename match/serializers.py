# match/serializers.py
from rest_framework import serializers
from .models import MatchSetting

class MatchSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = MatchSetting
        fields = ['id', 'preferred_gender', 'age_min', 'age_max', 'radius_km']
        read_only_fields = ['id']
