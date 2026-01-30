# apps/catches/models.py
import os
import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.competitions.models import Competition


def catch_photo_upload_to(instance: "Catch", filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    return (
        f"catches/competition_{instance.competition_id}/user_{instance.user_id}/"
        f"{uuid.uuid4().hex}{ext}"
    )


class Catch(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    competition = models.ForeignKey(
        Competition, on_delete=models.CASCADE, related_name="catches"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="catches"
    )

    species = models.CharField(max_length=120)
    length_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    weight_kg = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    caught_at = models.DateTimeField(default=timezone.now)
    note = models.TextField(blank=True)

    photo = models.ImageField(upload_to=catch_photo_upload_to)

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="catches_reviewed",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["competition", "status", "created_at"]),
            models.Index(fields=["user", "created_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(length_cm__isnull=True) | Q(length_cm__gt=0),
                name="catch_length_positive_or_null",
            ),
            models.CheckConstraint(
                check=Q(weight_kg__isnull=True) | Q(weight_kg__gt=0),
                name="catch_weight_positive_or_null",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.species} ({self.status})"
