# apps/notifications/models.py
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction

from apps.competitions.models import Competition


class Notification(models.Model):
    class Type(models.TextChoices):
        CATCH_CREATED = "CATCH_CREATED", "Catch created"
        CATCH_APPROVED = "CATCH_APPROVED", "Catch approved"
        CATCH_REJECTED = "CATCH_REJECTED", "Catch rejected"
        FRIEND_REQUEST = "FRIEND_REQUEST", "Friend request"
        FRIEND_ACCEPTED = "FRIEND_ACCEPTED", "Friend accepted"
        COMP_CANCELLED = "COMP_CANCELLED", "Competition cancelled"
        ORGANIZER_PROMOTED = "ORGANIZER_PROMOTED", "Organizer promoted"
        COMP_ADDED = "COMP_ADDED", "Added to competition"

    competition = models.ForeignKey(
        Competition, on_delete=models.CASCADE, related_name="notifications", null=True, blank=True
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )

    type = models.CharField(max_length=40, choices=Type.choices)
    payload = models.JSONField(default=dict, blank=True)

    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["recipient", "created_at"]),
            models.Index(fields=["competition", "created_at"]),
            # PostgreSQL: rýchly lookup neprečítaných
            models.Index(fields=["recipient"], name="notif_unread_recipient_idx", condition=Q(read_at__isnull=True)),
        ]

    def __str__(self) -> str:
        return f"{self.type} -> {self.recipient}"

    def mark_read(self, when=None):
        from django.utils import timezone
        self.read_at = when or timezone.now()
        self.save(update_fields=["read_at"])

# Nezabudni nechať importy nad tým nedotknuté

@receiver(post_save, sender=Notification, dispatch_uid="ws_notification_sender_unique")
def auto_broadcast_notification(sender, instance, created, **kwargs):
    print(f"--- DEBUG BE: Signál Notification (ID: {instance.id}) spustený. Created: {created} ---")
    if created:
        def send_ws():
            print(f"--- DEBUG BE: Odosielam cez WS do skupiny user_{instance.recipient_id} (Notif ID: {instance.id}) ---")
            from asgiref.sync import async_to_sync
            from channels.layers import get_channel_layer
            
            t = instance.type
            msg_title = "Nové upozornenie!"
            msg_text = "Máš novú správu."
            
            if t == "CATCH_CREATED":
                comp_name = instance.competition.name if instance.competition else ""
                msg_title = "Nový úlovok!"
                msg_text = f"Úlovok čaká na schválenie v súťaži {comp_name}."
            elif t == "CATCH_APPROVED":
                msg_title = "Úlovok schválený!"
                msg_text = f"Tvoj úlovok {instance.payload.get('species','')} bol schválený."
            elif t == "CATCH_REJECTED":
                msg_title = "Úlovok odmietnutý"
                msg_text = f"Tvoj úlovok {instance.payload.get('species','')} bol odmietnutý."
            elif t == "FRIEND_REQUEST":
                msg_title = "Žiadosť o priateľstvo"
                msg_text = f"Používateľ {instance.payload.get('sender_name','')} si ťa chce pridať."
            elif t == "FRIEND_ACCEPTED":
                msg_title = "Nové priateľstvo!"
                msg_text = f"Používateľ {instance.payload.get('sender_name','')} prijal tvoju žiadosť."
            elif t == "COMP_CANCELLED":
                msg_title = "Zrušená súťaž"
                msg_text = f"Súťaž {instance.payload.get('competition_name','')} bola zrušená."
            elif t == "ORGANIZER_PROMOTED":
                msg_title = "Nová rola!"
                msg_text = f"Bol si vymenovaný za organizátora v súťaži {instance.payload.get('competition_name','')}."
            elif t == "COMP_ADDED":
                msg_title = "Nová súťaž"
                msg_text = f"Bol si pridaný do súťaže {instance.payload.get('competition_name','')}."

            unread = Notification.objects.filter(recipient_id=instance.recipient_id, read_at__isnull=True).count()
            
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"user_{instance.recipient_id}",
                {
                    "type": "notify",
                    "data": {
                        "unread_count": unread,
                        "refresh_pending": False,
                        "message_title": msg_title, 
                        "message_text": msg_text,
                    },
                },
            )
        transaction.on_commit(send_ws)