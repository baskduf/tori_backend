from rest_framework import serializers
from .models import MatchSetting, MatchRequest
from django.contrib.auth import get_user_model

User = get_user_model()

class MatchSettingSerializer(serializers.ModelSerializer):
    age_range = serializers.ListField(child=serializers.IntegerField(), write_only=True)

    class Meta:
        model = MatchSetting
        fields = ['preferred_gender', 'age_range', 'radius_km']

    def create(self, validated_data):
        user = self.context['request'].user
        age_range = validated_data.pop('age_range')
        setting, _ = MatchSetting.objects.update_or_create(
            user=user,
            defaults={
                'preferred_gender': validated_data['preferred_gender'],
                'age_range_min': age_range[0],
                'age_range_max': age_range[1],
                'radius_km': validated_data['radius_km'],
            }
        )
        return setting


class MatchedUserSerializer(serializers.ModelSerializer):
    rating = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['username', 'age', 'gender', 'profile_image', 'rating']

    def get_rating(self, obj):
        # 예시: 평균 평가 점수
        return 4.5


class MatchDecisionSerializer(serializers.Serializer):
    match_id = serializers.IntegerField()
    decision = serializers.ChoiceField(choices=['accept', 'reject'])
