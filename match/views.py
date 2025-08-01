from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
import random

from .models import MatchSetting, MatchRequest, MatchQueue
from .serializers import (
    MatchSettingSerializer,
    MatchedUserSerializer,
    MatchDecisionSerializer
)

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
        queue, _ = MatchQueue.objects.get_or_create(user=user)
        queue.is_active = True
        queue.last_heartbeat = timezone.now()
        queue.save(update_fields=['is_active', 'last_heartbeat'])
        return Response({'message': '매칭 대기열에 입장했습니다.'})


class MatchHeartbeatView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            queue, _ = MatchQueue.objects.select_for_update().get_or_create(user=request.user)
            queue.last_heartbeat = timezone.now()
            queue.is_active = True
            queue.save(update_fields=['last_heartbeat', 'is_active'])

            # 매칭된 요청 확인 (내가 상대이거나 요청자일 수 있음)
            match = MatchRequest.objects.filter(
                matched_user=request.user, status='pending'
            ).first()

            if match:
                return Response({
                    'matched_user': MatchedUserSerializer(match.requester).data,
                    'match_id': match.id,
                    'show_time_sec': 7
                }, status=200)

            match = MatchRequest.objects.filter(
                requester=request.user, status='pending'
            ).first()

            if match:
                return Response({
                    'matched_user': MatchedUserSerializer(match.matched_user).data,
                    'match_id': match.id,
                    'show_time_sec': 7
                }, status=200)

            return Response({'message': '매칭 대기 중'})

        except MatchQueue.DoesNotExist:
            return Response({'message': '매칭 대기열에 없습니다.'}, status=400)


from django.db.models import Q

class MatchRandomView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        with transaction.atomic():
            queue, _ = MatchQueue.objects.select_for_update().get_or_create(user=user)
            queue.is_active = True
            queue.last_heartbeat = timezone.now()
            queue.save(update_fields=['is_active', 'last_heartbeat'])

            try:
                setting = MatchSetting.objects.get(user=user)
            except MatchSetting.DoesNotExist:
                return Response({'message': '매칭 조건을 먼저 설정하세요.'}, status=400)

            threshold = timezone.now() - timezone.timedelta(seconds=15)

            candidates = MatchQueue.objects.select_for_update().filter(
                is_active=True,
                last_heartbeat__gte=threshold,
                user__age__gte=setting.age_range_min,
                user__age__lte=setting.age_range_max
            ).exclude(user=user)

            if setting.preferred_gender != 'all':
                candidates = candidates.filter(user__gender=setting.preferred_gender)

            if not candidates.exists():
                return Response({'message': '조건에 맞는 유저가 없습니다.'}, status=404)

            matched_queue = random.choice(list(candidates))
            matched_user = matched_queue.user

            # 기존 매칭 요청이 있으면 해당 정보 리턴
            existing_match = MatchRequest.objects.filter(
                Q(requester=user, matched_user=matched_user) | Q(requester=matched_user, matched_user=user),
                status='pending'
            ).first()

            if existing_match:
                other_user = (existing_match.matched_user if existing_match.requester == user else existing_match.requester)
                return Response({
                    'matched_user': MatchedUserSerializer(other_user).data,
                    'show_time_sec': 7,
                    'match_id': existing_match.id,
                    'message': '이미 매칭 중인 상대가 있습니다.'
                })

            match_request = MatchRequest.objects.create(requester=user, matched_user=matched_user)
            queue.is_active = False
            matched_queue.is_active = False
            queue.save(update_fields=['is_active'])
            matched_queue.save(update_fields=['is_active'])

            return Response({
                'matched_user': MatchedUserSerializer(matched_user).data,
                'show_time_sec': 7,
                'match_id': match_request.id
            })

class MatchCancelView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            queue = MatchQueue.objects.get(user=request.user)
            queue.is_active = False
            queue.save(update_fields=['is_active'])
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
            match = MatchRequest.objects.get(id=match_id)
        except MatchRequest.DoesNotExist:
            return Response({'message': '매칭 요청을 찾을 수 없습니다.'}, status=404)

        if decision == 'accept':
            match.status = 'accepted'
        else:
            match.status = 'rejected'

        match.save()

        # 결정 이후 큐 비활성화 (방어적 처리)
        MatchQueue.objects.filter(user=request.user).update(is_active=False)

        return Response({'status': 'matched' if decision == 'accept' else 'next'})
