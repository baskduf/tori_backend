from django.db import models
from django.conf import settings

class MatchHistory(models.Model):
    user1 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='match_histories_1')
    user2 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='match_histories_2')
    matched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (('user1', 'user2'),)

from django.utils import timezone
from datetime import timedelta

class RecentMatchExclude(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='recent_excludes')
    excluded_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='excluded_by')
    excluded_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return timezone.now() > self.excluded_at + timedelta(minutes=5)  # 예: 5분 제외

    class Meta:
        indexes = [
            models.Index(fields=['user', 'excluded_user']),
        ]

class MatchSetting(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    age_min = models.PositiveIntegerField(default=18)
    age_max = models.PositiveIntegerField(default=99)
    radius_km = models.PositiveIntegerField(default=1)
    preferred_gender = models.CharField(max_length=10, choices=[('male','Male'), ('female','Female'), ('any','Any')], default='any')

class MatchQueue(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    entered_at = models.DateTimeField(auto_now_add=True)

class MatchRequest(models.Model):
    from_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='from_requests')
    to_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='to_requests')
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('accepted', 'Accepted'),
            ('rejected', 'Rejected'),
            ('matched', 'Matched')
        ],
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)

class MatchedRoom(models.Model):
    user1 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='matched_user1')
    user2 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='matched_user2')
    matched_at = models.DateTimeField(auto_now_add=True)
    # 추가로 채팅방 ID, 상태 등도 관리 가능
