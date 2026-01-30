# apps/notifications/models.py
from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.competitions.models import Competition


class Notification(models.Model):
    class Type(models.TextChoices):
        CATCH_CREATED = "CATCH_CREATED", "Catch created"
        CATCH_REVIEWED = "CATCH_REVIEWED", "Catch reviewed"

    competition = models.ForeignKey(
        Competition, on_delete=models.CASCADE, related_name="notifications"
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
