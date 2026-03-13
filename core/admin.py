from django.contrib import admin

from .models import DashboardFeedback


@admin.register(DashboardFeedback)
class DashboardFeedbackAdmin(admin.ModelAdmin):
    list_display = ("id", "feedback_type", "section", "reporter", "created_at")
    list_filter = ("feedback_type", "section", "created_at")
    search_fields = (
        "description",
        "reporter__email",
        "reporter__first_name",
        "reporter__last_name",
    )
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)