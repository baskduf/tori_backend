from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class MatchQueue(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='match_queue')
    entered_at = models.DateTimeField(auto_now_add=True)
    last_heartbeat = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)  # 매칭 활성 상태 표시 필드

    def is_still_active(self, timeout_seconds=15):
        return (timezone.now() - self.last_heartbeat).total_seconds() < timeout_seconds

class MatchSetting(models.Model):
    GENDER_CHOICES = (
        ('male', 'Male'),
        ('female', 'Female'),
        ('all', 'All'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    preferred_gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    age_range_min = models.IntegerField()
    age_range_max = models.IntegerField()
    radius_km = models.IntegerField()
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s settings"
    
class MatchRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    )

    requester = models.ForeignKey(User, related_name='match_requests', on_delete=models.CASCADE)
    matched_user = models.ForeignKey(User, related_name='matched_requests', on_delete=models.SET_NULL, null=True)
    
    requester_status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    matched_user_status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"MatchRequest from {self.requester} to {self.matched_user} [R:{self.requester_status} M:{self.matched_user_status}]"

