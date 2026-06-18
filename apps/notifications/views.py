from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.http import HttpResponseForbidden, HttpResponse
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


# apps/notifications/views.py

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
        .annotate(spot_number_annotated=Subquery(spot_subquery))
        .order_by("-created_at")
    )
    return render(request, "notifications/_pending_list.html", {"pending_catches": pending_catches})

@require_POST
@login_required
def mark_all_read(request):
    Notification.objects.filter(recipient=request.user, read_at__isnull=True).update(read_at=timezone.now())
    broadcast_unread_count(request.user.id, refresh_pending=False)

    if request.headers.get("HX-Request") == "true":
        resp = HttpResponse("")
        resp["HX-Trigger"] = "notificationsMarkedRead"
        return resp

    return redirect(request.POST.get("next") or "core:dashboard")


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

@require_POST
@login_required
def mark_read(request, notification_id):
    notif = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notif.mark_read()
    
    html_response = f"""
    <li class="d-flex align-items-start position-relative p-2 border-bottom text-wrap" style="opacity: 0.55; background-color: rgba(255,255,255,0.02);" id="notif-{notif.id}">
      <div class="me-2 mt-1">
        <i class="bi bi-check2-all text-success"></i>
      </div>
      <div class="flex-grow-1" style="font-size: 0.82rem; line-height: 1.3;">
        <span class="text-muted text-decoration-line-through">Upozornenie bolo vybavené.</span>
        <div class="text-muted d-flex justify-content-between align-items-center mt-1" style="font-size: 0.72rem;">
          <span>{notif.created_at.strftime('%d.%m.%Y %H:%M')}</span>
          <span class="text-success fw-semibold"><i class="bi bi-check"></i> prečítané</span>
        </div>
      </div>
    </li>
    """
    return HttpResponse(html_response)

@login_required
def notification_redirect(request, notification_id):
    notif = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notif.mark_read() 

    t = notif.type
    if t == Notification.Type.CATCH_CREATED:
        return redirect("notifications:pending")
    elif t in [Notification.Type.CATCH_APPROVED, Notification.Type.CATCH_REJECTED]:
        return redirect("catches:my_catches")
    elif t in [Notification.Type.FRIEND_REQUEST, Notification.Type.FRIEND_ACCEPTED]:
        return redirect("friends:home")
    elif t in [Notification.Type.COMP_CANCELLED, Notification.Type.COMP_ADDED, Notification.Type.ORGANIZER_PROMOTED, Notification.Type.OVERTAKEN]:
        if notif.competition_id:
            if t == Notification.Type.OVERTAKEN:
                return redirect("competitions:scoreboard", pk=notif.competition_id)
            return redirect("competitions:detail", pk=notif.competition_id)
        return redirect("competitions:my_competitions")
        
    return redirect("core:dashboard")
    