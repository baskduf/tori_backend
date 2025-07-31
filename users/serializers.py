# users/serializers.py
from rest_framework import serializers
from accounts.models import User  # User 모델은 accounts 앱에 있음

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'age', 'gender', 'profile_image']
        read_only_fields = ['age', 'gender']  # 수정 불가능하게 하려면
