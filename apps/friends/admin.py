from django.contrib import admin
from .models import Friendship


@admin.register(Friendship)
class FriendshipAdmin(admin.ModelAdmin):
    list_display = ("id", "user_a", "user_b", "status", "requested_by", "created_at", "responded_at")
    list_filter = ("status",)
    search_fields = ("user_a__username", "user_b__username", "user_a__first_name", "user_a__last_name", "user_b__first_name", "user_b__last_name")
    autocomplete_fields = ("user_a", "user_b", "requested_by")
