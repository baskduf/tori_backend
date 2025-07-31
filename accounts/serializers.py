from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()

class SignUpSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'password', 'age', 'gender', 'profile_image']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)  # 비밀번호 해시화
        user.save()
        return user

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('username', 'age', 'gender', 'profile_image')
        read_only_fields = ('username',)

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('age', 'gender', 'profile_image')
