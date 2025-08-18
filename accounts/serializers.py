from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework.validators import UniqueValidator
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework import serializers
from django.contrib.auth import authenticate

User = get_user_model()

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        # username, password로 authenticate 호출
        user = authenticate(
            username=attrs.get("username"),
            password=attrs.get("password")
        )
        if not user:
            raise serializers.ValidationError({
                "detail": "아이디 또는 비밀번호가 잘못되었습니다."
            })
        if not user.is_active:
            raise serializers.ValidationError({
                "detail": "비활성 계정입니다. 관리자에게 문의하세요."
            })
        # JWT 토큰 발급
        data = super().validate(attrs)
        return data



class SignUpSerializer(serializers.ModelSerializer):
    username = serializers.CharField(
        validators=[
            UniqueValidator(
                queryset=User.objects.all(),
                message="이미 사용 중인 아이디입니다."
            )
        ],
        error_messages={
            'blank': '아이디를 입력해주세요.',
            'required': '아이디는 필수 입력 항목입니다.'
        }
    )
    
    password = serializers.CharField(
        write_only=True,
        error_messages={
            'blank': '비밀번호를 입력해주세요.',
            'required': '비밀번호는 필수 입력 항목입니다.'
        }
    )
    
    age = serializers.IntegerField(
        min_value=1,
        error_messages={
            'required': '나이를 입력해주세요.',
            'invalid': '유효한 숫자를 입력해주세요.',
            'min_value': '나이는 1 이상이어야 합니다.'
        }
    )
    
    gender = serializers.ChoiceField(
        choices=User.GENDER_CHOICES,
        error_messages={
            'required': '성별을 선택해주세요.',
            'invalid_choice': '유효한 성별을 선택해주세요.'
        }
    )
    
    profile_image = serializers.ImageField(
        required=False,
        allow_null=True,
        error_messages={
            'invalid': '유효한 이미지 파일을 업로드해주세요.'
        }
    )

    class Meta:
        model = User
        fields = ['username', 'password', 'age', 'gender', 'profile_image']

    def validate_password(self, value):
        # settings.py의 AUTH_PASSWORD_VALIDATORS 기반 검증
        validate_password(value)
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('username', 'age', 'gender', 'profile_image','email')
        read_only_fields = ('username',)

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('age', 'gender', 'profile_image')

# accounts/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()

class SocialSignupSerializer(serializers.ModelSerializer):
    username = serializers.CharField(
        error_messages={'blank': '아이디를 입력해주세요.', 'required': '아이디는 필수 입력 항목입니다.'}
    )
    age = serializers.IntegerField(
        min_value=1,
        error_messages={'required': '나이를 입력해주세요.', 'min_value': '나이는 1 이상이어야 합니다.'}
    )
    gender = serializers.ChoiceField(
        choices=User.GENDER_CHOICES,
        error_messages={'required': '성별을 선택해주세요.', 'invalid_choice': '유효한 성별을 선택해주세요.'}
    )
    profile_image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = ['username', 'age', 'gender', 'profile_image']

    def create(self, validated_data):
        user = User(**validated_data)
        user.save()
        return user
