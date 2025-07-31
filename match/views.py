from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import MatchSetting, MatchRequest
from .serializers import MatchSettingSerializer, MatchedUserSerializer, MatchDecisionSerializer
from django.contrib.auth import get_user_model
from django.db.models import Q
import random

User = get_user_model()


# 2.1 매칭 조건 저장
class MatchSettingView(generics.CreateAPIView):
    serializer_class = MatchSettingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'message': '매칭 조건이 저장되었습니다.'})


class MatchRandomView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        # 매칭 중임을 표시
        if not user.is_matching:
            user.is_matching = True
            user.save(update_fields=['is_matching'])

        try:
            setting = MatchSetting.objects.get(user=user)
        except MatchSetting.DoesNotExist:
            return Response({'message': '매칭 조건을 먼저 설정하세요.'}, status=400)

        candidates = User.objects.filter(
            is_matching=True,                # 매칭 중인 사용자만 후보군
            age__gte=setting.age_range_min,
            age__lte=setting.age_range_max
        ).exclude(id=user.id)

        if setting.preferred_gender != 'all':
            candidates = candidates.filter(gender=setting.preferred_gender)

        if not candidates.exists():
            # 매칭 후보가 없으면 is_matching 다시 False로 바꿈
            user.is_matching = True
            user.save(update_fields=['is_matching'])

            return Response({'message': '조건에 맞는 유저가 없습니다.'}, status=404)

        matched_user = random.choice(candidates)
        match_request = MatchRequest.objects.create(requester=user, matched_user=matched_user)

        return Response({
            'matched_user': MatchedUserSerializer(matched_user).data,
            'show_time_sec': 7,
            'match_id': match_request.id,
        })
    
class MatchCancelView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.is_matching:
            user.is_matching = False
            user.save(update_fields=['is_matching'])
        return Response({'message': '매칭 상태가 해제되었습니다.'})

class MatchDecisionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = MatchDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        match_id = serializer.validated_data['match_id']
        decision = serializer.validated_data['decision']

        try:
            match_request = MatchRequest.objects.get(id=match_id, requester=request.user)
        except MatchRequest.DoesNotExist:
            return Response({'message': '매칭 요청을 찾을 수 없습니다.'}, status=404)

        match_request.status = 'accepted' if decision == 'accept' else 'rejected'
        match_request.save()

        # 매칭 결정 후 매칭 중 상태 해제
        user = request.user
        if user.is_matching:
            user.is_matching = False
            user.save(update_fields=['is_matching'])

        return Response({'status': 'matched' if decision == 'accept' else 'next'})
