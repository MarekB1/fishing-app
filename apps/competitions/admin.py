from django.contrib import admin
from .models import Competition, CompetitionMembership, Invitation


@admin.register(Competition)
class CompetitionAdmin(admin.ModelAdmin):
    list_display = ("name", "starts_at", "ends_at", "created_by", "created_at")
    list_filter = ("starts_at", "ends_at")
    search_fields = ("name",)


@admin.register(CompetitionMembership)
class CompetitionMembershipAdmin(admin.ModelAdmin):
    list_display = ("competition", "user", "role", "joined_at")
    list_filter = ("role",)
    search_fields = ("competition__name", "user__username", "user__email")


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ("competition", "email", "invited_user", "token", "expires_at", "used_at", "created_at")
    list_filter = ("used_at",)
    search_fields = ("competition__name", "email", "token")
