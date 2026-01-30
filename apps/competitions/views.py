from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .models import Competition, CompetitionMembership


def _status_for_competition(c: Competition) -> str:
    now = timezone.now()
    if now < c.starts_at:
        return "plánovaná"
    if now > c.ends_at:
        return "ukončená"
    return "prebieha"


@login_required
def my_competitions(request):
    memberships = (
        CompetitionMembership.objects
        .filter(user=request.user)
        .select_related("competition")
        .order_by("-competition__starts_at")
    )

    items = []
    for m in memberships:
        c = m.competition
        items.append({
            "competition": c,
            "name": c.name,
            "starts": c.starts_at,
            "ends": c.ends_at,
            "status": _status_for_competition(c),
            "role": m.get_role_display(),  # Organizer / Contestant
        })

    return render(request, "competitions/my_competitions.html", {
        "items": items,
    })


@login_required
def competition_detail(request, pk: int):
    competition = get_object_or_404(Competition, pk=pk)

    membership = (
        CompetitionMembership.objects
        .filter(competition=competition, user=request.user)
        .first()
    )

    # Bezpečnosť: do detailu pustíme len člena súťaže alebo tvorcu
    is_creator = (competition.created_by_id == request.user.id)
    if membership is None and not is_creator:
        raise Http404("Competition not found")

    # Ak tvorca nemá membership (môže sa stať), berieme ho ako organizer
    is_organizer = is_creator or (membership and membership.role == CompetitionMembership.Role.ORGANIZER)
    is_contestant = (membership and membership.role == CompetitionMembership.Role.CONTESTANT)

    context = {
        "competition": competition,
        "membership": membership,
        "status": _status_for_competition(competition),
        "is_organizer": bool(is_organizer),
        "is_contestant": bool(is_contestant),
    }
    return render(request, "competitions/detail.html", context)
