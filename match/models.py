from django.db import models

# Create your models here.
# match/models.py

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class MatchQueue(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='match_queue')
    entered_at = models.DateTimeField(auto_now_add=True)
    last_heartbeat = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

class MatchRequest(models.Model):
    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name="requested_matches")
    matched_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="matched_by")
    status = models.CharField(max_length=10, choices=[("pending", "Pending"), ("accepted", "Accepted"), ("rejected", "Rejected")])
    created_at = models.DateTimeField(auto_now_add=True)

class MatchSetting(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    preferred_gender = models.CharField(max_length=10, choices=[("male", "Male"), ("female", "Female"), ("all", "All")])
    age_range_min = models.IntegerField()
    age_range_max = models.IntegerField()
    radius_km = models.IntegerField()
    updated_at = models.DateTimeField(auto_now=True)
