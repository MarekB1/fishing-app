from django.contrib import admin
from .models import Catch


@admin.register(Catch)
class CatchAdmin(admin.ModelAdmin):
    list_display = ("competition", "user", "species", "status", "caught_at", "created_at")
    list_filter = ("status", "competition")
    search_fields = ("species", "user__username", "user__email")
