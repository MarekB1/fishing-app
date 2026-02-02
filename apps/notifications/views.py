from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.catches.models import Catch
from apps.competitions.models import Competition, CompetitionMembership
from .models import Notification
from .realtime import broadcast_unread_count

def _organizer_competitions(user):
    return (
        Competition.objects.filter(
            Q(created_by=user) |
            Q(memberships__user=user, memberships__role=CompetitionMembership.Role.ORGANIZER)
        )
        .distinct()
    )

@login_required
def pending(request):
    return render(request, "notifications/pending.html")

@login_required
def pending_list(request):
    comps = _organizer_competitions(request.user)
    pending_catches = (
        Catch.objects.filter(competition__in=comps, status=Catch.Status.PENDING)
        .select_related("competition", "user")
        .order_by("-created_at")
    )
    return render(request, "notifications/_pending_list.html", {"pending_catches": pending_catches})

@require_POST
@login_required
def mark_all_read(request):
    Notification.objects.filter(recipient=request.user, read_at__isnull=True).update(read_at=timezone.now())
    broadcast_unread_count(request.user.id, refresh_pending=False)
    return redirect("notifications:pending")
