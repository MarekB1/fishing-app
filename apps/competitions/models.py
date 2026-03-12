# apps/competitions/models.py
import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.core.validators import MinValueValidator

class Competition(models.Model):
    class Tier(models.TextChoices):
        UNOFFICIAL = "UNOFFICIAL", "Neoficiálna"
        OFFICIAL = "OFFICIAL", "Oficiálna"

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    tier = models.CharField(
        max_length=12,
        choices=Tier.choices,
        default=Tier.UNOFFICIAL,
        db_index=True,
    )

    cancelled_at = models.DateTimeField(null=True, blank=True, db_index=True)

    location_name = models.CharField(max_length=255, default="")  # názov miesta
    fishing_spots_count = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
    )  # počet miest
    allow_photos = models.BooleanField(default=True)  # povoliť fotky úlovkov

    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()

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
        permissions = [
            ("premium", "Premium"),
        ]

    def __str__(self) -> str:
        return self.name
    
    @property
    def is_official(self) -> bool:
        return self.tier == self.Tier.OFFICIAL

    @property
    def max_contestants(self):
        """UNOFFICIAL: max 5 contestantov, OFFICIAL: bez limitu."""
        return None if self.is_official else 5
    
    @property
    def is_cancelled(self) -> bool:
        return self.cancelled_at is not None
    
    @property
    def is_running(self) -> bool:
        if self.is_cancelled:
            return False
        now = timezone.now()
        return self.starts_at <= now <= self.ends_at


class CompetitionMembership(models.Model):
    class Role(models.TextChoices):
        ORGANIZER = "ORGANIZER", "Organizátor"
        CONTESTANT = "CONTESTANT", "Súťažiaci"

    competition = models.ForeignKey(
        Competition, on_delete=models.CASCADE, related_name="memberships"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="competition_memberships"
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    is_organizer = models.BooleanField(default=False, db_index=True)

    spot_number = models.PositiveSmallIntegerField(null=True, blank=True, db_index=True)

    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["competition", "user"],
                name="uniq_membership_competition_user",
            ),
            models.UniqueConstraint(
                fields=["competition", "spot_number"],
                condition=Q(spot_number__isnull=False),
                name="uniq_membership_competition_spot_number",
            ),
        ]

        indexes = [
            models.Index(fields=["competition", "role"]),
            models.Index(fields=["competition", "is_organizer"]),
            models.Index(fields=["user"]),
        ]

    def __str__(self) -> str:
        return f"{self.user} @ {self.competition} ({self.role}, organizer={self.is_organizer})"


class Invitation(models.Model):
    class Kind(models.TextChoices):
        DIRECT = "DIRECT", "Direct (single-use)"   # email / jednorazová
        LINK = "LINK", "Share link (multi-use)"    # zdieľateľná

    competition = models.ForeignKey(
        "Competition", on_delete=models.CASCADE, related_name="invitations"
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="competition_invites_created",
    )

    kind = models.CharField(
        max_length=12,
        choices=Kind.choices,
        default=Kind.DIRECT,
        db_index=True,
    )

    # DIRECT: pozývanie buď emailom, alebo priamo userom (stačí jedno)
    email = models.EmailField(blank=True, null=True)
    invited_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="competition_invitations",
    )

    spot_number = models.PositiveSmallIntegerField(null=True, blank=True, db_index=True)

    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    # LINK: limity použitia (null = neobmedzené)
    max_uses = models.PositiveIntegerField(null=True, blank=True)
    uses_count = models.PositiveIntegerField(default=0)

    expires_at = models.DateTimeField(null=True, blank=True)

    # DIRECT: jednorazové použitie
    used_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["token"]),
            models.Index(fields=["competition", "kind"]),
            models.Index(fields=["competition", "used_at"]),
        ]
        constraints = [
            # 1 share-link (LINK) na súťaž (PostgreSQL partial unique)
            models.UniqueConstraint(
                fields=["competition"],
                condition=Q(kind="LINK"),
                name="uniq_competition_share_link",
            )
        ]

    def __str__(self) -> str:
        return f"Invite {self.token} -> {self.competition} ({self.kind})"

    def is_valid(self) -> bool:
        now = timezone.now()

        if self.expires_at and now > self.expires_at:
            return False

        if self.kind == self.Kind.DIRECT:
            return self.used_at is None

        # LINK:
        if self.max_uses is not None and self.uses_count >= self.max_uses:
            return False
        return True


class InvitationUse(models.Model):
    """Log použitia multi-use linku (1x per user)."""
    invitation = models.ForeignKey(
        Invitation, on_delete=models.CASCADE, related_name="uses"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="competition_invite_uses",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["invitation", "user"],
                name="uniq_invitation_use_invitation_user",
            )
        ]
        indexes = [
            models.Index(fields=["invitation", "created_at"]),
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} used {self.invitation_id}"
