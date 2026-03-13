from django.conf import settings
from django.db import models


class DashboardFeedback(models.Model):
    class Section(models.TextChoices):
        COMPETITIONS = "competitions", "Súťaže"
        COMPETITION_CREATE = "competition_create", "Nová súťaž"
        INVITATIONS = "invitations", "Pozvánky"
        CATCH_CREATE = "catch_create", "Pridať úlovok"
        PENDING_CATCHES = "pending_catches", "Čaká na schválenie"
        SCOREBOARD = "scoreboard", "Scoreboard"
        MY_CATCHES = "my_catches", "Moje úlovky"

    class FeedbackType(models.TextChoices):
        BUG = "bug", "Bug"
        IMPROVEMENT = "improvement", "Zlepšenie"

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="dashboard_feedbacks",
        verbose_name="Tester",
    )
    section = models.CharField(
        max_length=32,
        choices=Section.choices,
        verbose_name="Sekcia",
    )
    feedback_type = models.CharField(
        max_length=16,
        choices=FeedbackType.choices,
        verbose_name="Typ",
    )
    description = models.TextField(verbose_name="Popis")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Vytvorené")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Upravené")

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Poznámka z dashboardu"
        verbose_name_plural = "Poznámky z dashboardu"
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["section", "feedback_type"]),
            models.Index(fields=["reporter", "created_at"]),
        ]

    def __str__(self):
        return f"{self.get_feedback_type_display()} • {self.get_section_display()} • {self.reporter}"