from django.contrib import admin
from django.contrib.admin.sites import NotRegistered
from .models import Competition, CompetitionMembership, Invitation


class CompetitionAdmin(admin.ModelAdmin):
    list_display = ("name", "tier", "starts_at", "ends_at", "created_by", "created_at")
    list_filter = ("tier", "starts_at", "ends_at")
    search_fields = ("name",)


class CompetitionMembershipAdmin(admin.ModelAdmin):
    list_display = ("competition", "user", "role", "joined_at")
    list_filter = ("role",)
    search_fields = ("competition__name", "user__username", "user__email")


class InvitationAdmin(admin.ModelAdmin):
    list_display = ("competition", "email", "invited_user", "token", "expires_at", "used_at", "created_at")
    list_filter = ("used_at",)
    search_fields = ("competition__name", "email", "token")


# ✅ Bezpečná registrácia (ak sa admin importne 2×, nespadne to)
for model, admin_cls in (
    (Competition, CompetitionAdmin),
    (CompetitionMembership, CompetitionMembershipAdmin),
    (Invitation, InvitationAdmin),
):
    try:
        admin.site.unregister(model)
    except NotRegistered:
        pass
    admin.site.register(model, admin_cls)
