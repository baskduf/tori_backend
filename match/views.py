from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import MatchSetting, MatchRequest, MatchQueue
from .serializers import MatchSettingSerializer, MatchedUserSerializer, MatchDecisionSerializer
from django.contrib.auth import get_user_model
from django.utils import timezone
import random

User = get_user_model()

class MatchSettingView(generics.CreateAPIView):
    serializer_class = MatchSettingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'message': '매칭 조건이 저장되었습니다.'})

class EnterMatchQueueView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        mq, created = MatchQueue.objects.get_or_create(user=user)
        mq.is_active = True
        mq.last_heartbeat = timezone.now()
        mq.save(update_fields=['is_active', 'last_heartbeat'])
        return Response({'message': '매칭 대기열에 입장했습니다.'})

class MatchHeartbeatView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            mq = MatchQueue.objects.get(user=request.user)
            mq.last_heartbeat = timezone.now()
            mq.is_active = True
            mq.save(update_fields=['last_heartbeat', 'is_active'])
            return Response({'message': '하트비트 갱신 완료'})
        except MatchQueue.DoesNotExist:
            return Response({'message': '매칭 대기열에 없습니다.'}, status=400)

class MatchRandomView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        # 1. 대기열에 없으면 등록
        queue, created = MatchQueue.objects.get_or_create(user=user)
        if created or not queue.is_active:
            queue.is_active = True
            queue.last_heartbeat = timezone.now()
            queue.save(update_fields=['is_active', 'last_heartbeat'])

        # 2. 매칭 조건 가져오기
        try:
            setting = MatchSetting.objects.get(user=user)
        except MatchSetting.DoesNotExist:
            return Response({'message': '매칭 조건을 먼저 설정하세요.'}, status=400)

        # 3. 하트비트 기준 유효한 대기열 필터 (15초 기준 예)
        heartbeat_timeout_sec = 15
        threshold_time = timezone.now() - timezone.timedelta(seconds=heartbeat_timeout_sec)

        # 4. 조건에 맞는 다른 유저 후보 필터링
        candidates = MatchQueue.objects.filter(
            is_active=True,
            last_heartbeat__gte=threshold_time,
            user__age__gte=setting.age_range_min,
            user__age__lte=setting.age_range_max,
        ).exclude(user=user)

        if setting.preferred_gender != 'all':
            candidates = candidates.filter(user__gender=setting.preferred_gender)

        if not candidates.exists():
            return Response({'message': '조건에 맞는 유저가 없습니다.'}, status=404)

        matched_queue = random.choice(list(candidates))
        matched_user = matched_queue.user

        # 5. 매칭 요청 생성
        match_request = MatchRequest.objects.create(requester=user, matched_user=matched_user)

        # 6. 두 유저 대기열 비활성화 처리
        queue.is_active = False
        matched_queue.is_active = False
        queue.save(update_fields=['is_active'])
        matched_queue.save(update_fields=['is_active'])

        return Response({
            'matched_user': MatchedUserSerializer(matched_user).data,
            'show_time_sec': 7,
            'match_id': match_request.id,
        })

class MatchCancelView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            mq = MatchQueue.objects.get(user=request.user)
            mq.is_active = False
            mq.save(update_fields=['is_active'])
            return Response({'message': '매칭 상태가 해제되었습니다.'})
        except MatchQueue.DoesNotExist:
            return Response({'message': '매칭 대기열에 없습니다.'}, status=400)

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

        # 매칭 결정 후 매칭 대기열 비활성화 (대기 상태 해제)
        try:
            mq = MatchQueue.objects.get(user=request.user)
            mq.is_active = False
            mq.save(update_fields=['is_active'])
        except MatchQueue.DoesNotExist:
            pass

        return Response({'status': 'matched' if decision == 'accept' else 'next'})
