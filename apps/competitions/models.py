# apps/competitions/models.py
import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Competition(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()

    # jednoduché, rozšírime neskôr (napr. scoring config)
    scoring_rules = models.JSONField(default=dict, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="competitions_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["starts_at"]),
            models.Index(fields=["ends_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(ends_at__gt=models.F("starts_at")),
                name="competition_ends_after_starts",
            )
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def is_running(self) -> bool:
        now = timezone.now()
        return self.starts_at <= now <= self.ends_at


class CompetitionMembership(models.Model):
    class Role(models.TextChoices):
        ORGANIZER = "ORGANIZER", "Organizer"
        CONTESTANT = "CONTESTANT", "Contestant"

    competition = models.ForeignKey(
        Competition, on_delete=models.CASCADE, related_name="memberships"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="competition_memberships"
    )
    role = models.CharField(max_length=20, choices=Role.choices)

    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["competition", "user"],
                name="uniq_membership_competition_user",
            )
        ]
        indexes = [
            models.Index(fields=["competition", "role"]),
            models.Index(fields=["user"]),
        ]

    def __str__(self) -> str:
        return f"{self.user} @ {self.competition} ({self.role})"


class Invitation(models.Model):
    competition = models.ForeignKey(
        Competition, on_delete=models.CASCADE, related_name="invitations"
    )

    # pozývanie buď emailom, alebo priamo userom (stačí jedno)
    email = models.EmailField(blank=True, null=True)
    invited_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="competition_invitations",
    )

    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    expires_at = models.DateTimeField(null=True, blank=True)
    used_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["token"]),
            models.Index(fields=["competition", "used_at"]),
        ]

    def __str__(self) -> str:
        return f"Invite {self.token} -> {self.competition}"

    def is_valid(self) -> bool:
        if self.used_at is not None:
            return False
        if self.expires_at is None:
            return True
        return timezone.now() <= self.expires_at
