from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.competitions.models import CompetitionMembership
from apps.notifications.models import Notification
from apps.notifications.realtime import broadcast_unread_count
from .models import Catch


@receiver(post_save, sender=Catch)
def catch_created_notify_organizers(sender, instance: Catch, created: bool, **kwargs):
    if not created:
        return
    if instance.status != Catch.Status.PENDING:
        return

    competition = instance.competition

    organizer_ids = set(
        CompetitionMembership.objects.filter(
            competition=competition,
            role=CompetitionMembership.Role.ORGANIZER,
        ).values_list("user_id", flat=True)
    )
    organizer_ids.add(competition.created_by_id)
    organizer_ids.discard(instance.user_id)  # nech si to neposiela sám sebe

    for uid in organizer_ids:
        Notification.objects.create(
            competition=competition,
            recipient_id=uid,
            type=Notification.Type.CATCH_CREATED,
            payload={
                "catch_id": instance.id,
                "species": instance.species,
                "contestant_id": instance.user_id,
            },
        )

        # WS až po commite (aby druhý tab už videl DB stav)
        transaction.on_commit(lambda uid=uid: broadcast_unread_count(uid, refresh_pending=True))
