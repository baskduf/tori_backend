from django.db import models
from django.conf import settings  # 추가

class MatchQueue(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,  # 문자열로 변경
        on_delete=models.CASCADE,
        related_name='match_queue'
    )
    entered_at = models.DateTimeField(auto_now_add=True)
    last_heartbeat = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

class MatchRequest(models.Model):
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="requested_matches"
    )
    matched_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="matched_by"
    )
    status = models.CharField(
        max_length=10,
        choices=[("pending", "Pending"), ("accepted", "Accepted"), ("rejected", "Rejected")]
    )
    created_at = models.DateTimeField(auto_now_add=True)

class MatchSetting(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    preferred_gender = models.CharField(
        max_length=10,
        choices=[("male", "Male"), ("female", "Female"), ("all", "All")]
    )
    age_range_min = models.IntegerField()
    age_range_max = models.IntegerField()
    radius_km = models.IntegerField()
    updated_at = models.DateTimeField(auto_now=True)
