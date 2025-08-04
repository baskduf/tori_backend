# match/matchmaker.py
from .models import MatchQueue, MatchSetting, MatchRequest
from django.utils import timezone
from datetime import timedelta

def match_users():
    active_users = MatchQueue.objects.filter(is_active=True)

    for user_q in active_users:
        # 선호 조건 조회
        setting = MatchSetting.objects.filter(user=user_q.user).first()
        if not setting:
            continue

        # 다른 후보 검색
        candidates = MatchQueue.objects.exclude(user=user_q.user).filter(
            is_active=True,
            user__gender__in=[setting.preferred_gender, 'all'] if setting.preferred_gender != 'all' else ['male', 'female']
        )

        # 나이/거리 조건 등 추가 필터링 가능

        for candidate in candidates:
            # 둘 다 매칭 안된 경우
            already_requested = MatchRequest.objects.filter(
                requester=user_q.user, matched_user=candidate.user, status="pending"
            ).exists()
            if not already_requested:
                MatchRequest.objects.create(
                    requester=user_q.user,
                    matched_user=candidate.user,
                    status="pending"
                )
                # 여기서 WebSocket 메시지 전송
                # channel_layer.group_send() 사용
                break
