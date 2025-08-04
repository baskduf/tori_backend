# match/serializers.py
from rest_framework import serializers
from .models import MatchSetting

class MatchSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = MatchSetting
        fields = ['id', 'preferred_gender', 'age_range_min', 'age_range_max', 'radius_km', 'updated_at']
        read_only_fields = ['id', 'updated_at']
