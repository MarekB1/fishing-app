from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Friendship(models.Model):
    """Jeden záznam na dvojicu userov (poradie sa kanonizuje: user_a_id < user_b_id).

    - status=PENDING: čaká na potvrdenie druhým userom
    - status=ACCEPTED: priatelia
    - status=DECLINED: zamietnuté / zrušené
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACCEPTED = "ACCEPTED", "Accepted"
        DECLINED = "DECLINED", "Declined"

    user_a = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="friendships_a",
    )
    user_b = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="friendships_b",
    )

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="friendships_requested",
        help_text="Kto poslal žiadosť",
    )

    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user_a", "user_b"], name="uniq_friendship_pair"),
            models.CheckConstraint(check=~Q(user_a=models.F("user_b")), name="friendship_not_self"),
        ]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["user_a", "status"]),
            models.Index(fields=["user_b", "status"]),
        ]

    def save(self, *args, **kwargs):
        # kanonické poradie dvojice
        if self.user_a_id and self.user_b_id and self.user_a_id > self.user_b_id:
            self.user_a_id, self.user_b_id = self.user_b_id, self.user_a_id
        super().save(*args, **kwargs)

    def other_user(self, me):
        if self.user_a_id == getattr(me, "id", None):
            return self.user_b
        return self.user_a

    @classmethod
    def pair_q(cls, user1_id: int, user2_id: int) -> Q:
        """Filter na dvojicu bez ohľadu na poradie."""
        a, b = sorted([user1_id, user2_id])
        return Q(user_a_id=a, user_b_id=b)

    def mark_accepted(self):
        self.status = self.Status.ACCEPTED
        self.responded_at = timezone.now()
        self.save(update_fields=["status", "responded_at", "updated_at"])

    def mark_declined(self):
        self.status = self.Status.DECLINED
        self.responded_at = timezone.now()
        self.save(update_fields=["status", "responded_at", "updated_at"])

    def __str__(self) -> str:
        return f"{self.user_a_id} <-> {self.user_b_id} ({self.status})"
