from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.db.models import Q, OuterRef, Subquery
from apps.competitions.models import Competition, CompetitionMembership

from apps.catches.models import Catch
from apps.competitions.models import Competition
from .models import Notification
from .realtime import broadcast_unread_count

def _organizer_competitions(user):
    return (
        Competition.objects.filter(
            Q(created_by=user) |
            Q(memberships__user=user, memberships__is_organizer=True)
        )
        .distinct()
    )

@login_required
def pending(request):
    blocked = _require_organizer(request)
    if blocked:
        return blocked
    return render(request, "notifications/pending.html")


@login_required
def pending_list(request):
    blocked = _require_organizer(request)
    if blocked:
        return blocked

    comps = _organizer_competitions(request.user)

    spot_subquery = CompetitionMembership.objects.filter(
        competition_id=OuterRef("competition_id"),
        user_id=OuterRef("user_id"),
    ).values("spot_number")[:1]

    pending_catches = (
        Catch.objects.filter(competition__in=comps, status=Catch.Status.PENDING)
        .select_related("competition", "user")
        .annotate(spot_number=Subquery(spot_subquery))
        .order_by("-created_at")
    )
    return render(request, "notifications/_pending_list.html", {"pending_catches": pending_catches})

@require_POST
@login_required
def mark_all_read(request):
    blocked = _require_organizer(request)
    if blocked:
        return blocked

    Notification.objects.filter(recipient=request.user, read_at__isnull=True).update(read_at=timezone.now())
    broadcast_unread_count(request.user.id, refresh_pending=False)
    return redirect("notifications:pending")


def _require_organizer(request):
    """
    - Ak user nie je organizer (nemá ani jednu súťaž kde je organizer/creator), nepustíme ho do Pending.
    - Pre HTMX volania (partial) vrátime 403, aby sa to nedalo obchádzať.
    """
    if _organizer_competitions(request.user).exists():
        return None

    if request.headers.get("HX-Request") == "true":
        return HttpResponseForbidden("Organizer only")

    messages.error(request, "Táto sekcia je dostupná len pre organizátora súťaže.")
    return redirect("core:dashboard")
