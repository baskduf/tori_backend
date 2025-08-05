from django.contrib.auth import get_user_model
from django.db.models import Q
from channels.db import database_sync_to_async
from .models import MatchQueue, MatchRequest, MatchSetting, MatchedRoom

User = get_user_model()

class MatchService:
    def __init__(self, user):
        self.user = user

    @database_sync_to_async
    def add_to_queue(self):
        MatchQueue.objects.update_or_create(user=self.user, defaults={"is_active": True})

    @database_sync_to_async
    def remove_from_queue(self):
        MatchQueue.objects.filter(user=self.user).update(is_active=False)

    @database_sync_to_async
    def get_my_setting(self):
        return MatchSetting.objects.filter(user=self.user).first()

    @database_sync_to_async
    def get_eligible_user(self, setting):
        qs = MatchQueue.objects.filter(is_active=True).exclude(user=self.user)
        for mq in qs:
            try:
                other_setting = MatchSetting.objects.get(user=mq.user)
            except MatchSetting.DoesNotExist:
                continue

            if not (setting.age_min <= other_setting.user.age <= setting.age_max):
                continue
            if setting.preferred_gender != 'any' and other_setting.user.gender != setting.preferred_gender:
                continue
            if other_setting.preferred_gender != 'any' and setting.user.gender != other_setting.preferred_gender:
                continue

            return mq.user
        return None

    @database_sync_to_async
    def create_match_request(self, other_user):
        MatchRequest.objects.create(from_user=self.user, to_user=other_user, status='matched')

    @database_sync_to_async
    def get_current_match_requests(self):
        return list(
            MatchRequest.objects.filter(
                Q(from_user=self.user) | Q(to_user=self.user)
            )
        )

    @database_sync_to_async
    def cleanup_matches(self, matches):
        for match in matches:
            match.delete()

    @database_sync_to_async
    def get_current_match_request(self):
        return MatchRequest.objects.filter(
            Q(from_user=self.user) | Q(to_user=self.user)
        ).first()

    @database_sync_to_async
    def get_match_request(self, partner_name):
        try:
            partner = User.objects.get(username=partner_name)
        except User.DoesNotExist:
            return None

        return MatchRequest.objects.select_related('from_user', 'to_user').filter(
            from_user__in=[self.user, partner],
            to_user__in=[self.user, partner],
            status__in=['matched', 'accepted']
        ).first()

    @database_sync_to_async
    def update_match_status_and_create_room(self, match, response):
        other_user = match.to_user if match.from_user == self.user else match.from_user

        if response == 'accept':
            other_accepted = MatchRequest.objects.filter(
                from_user__in=[self.user, other_user],
                to_user__in=[self.user, other_user],
                status__in=['accepted']
            ).first()

            if other_accepted:
                match.status = 'success'
                other_accepted.status = 'success'
                match.save()
                other_accepted.save()

                MatchedRoom.objects.create(user1=self.user, user2=other_user)

                match.delete()
                other_accepted.delete()

                MatchQueue.objects.filter(user__in=[self.user, other_user]).delete()

                return ("success", other_user)
            else:
                match.status = 'accepted'
                match.save()
                return ("accepted", None)

        else:
            match.delete()
            MatchQueue.objects.filter(user__in=[self.user, other_user]).update(is_active=True)
            return ("rejected", None)

    @database_sync_to_async
    def get_partner(self, match):
        return match.from_user if match.to_user == self.user else match.to_user
