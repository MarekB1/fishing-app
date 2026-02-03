from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.shortcuts import redirect, render
from django.db import transaction
from django.db.models import Q
from django.urls import reverse

from .forms import CompetitionForm
from .models import Competition, CompetitionMembership, Invitation
from .forms import InvitationCreateForm
from apps.catches.models import Catch
from django.contrib.auth.views import redirect_to_login


def _status_for_competition(c: Competition) -> str:
    now = timezone.now()
    if now < c.starts_at:
        return "plánovaná"
    if now > c.ends_at:
        return "ukončená"
    return "prebieha"

def _organizer_competitions_qs(user):
    return (
        Competition.objects
        .filter(
            Q(created_by=user)
            | Q(memberships__user=user, memberships__role=CompetitionMembership.Role.ORGANIZER)
        )
        .distinct()
        .order_by("-starts_at")
    )


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
def competition_create(request):
    if request.method == "POST":
        form = CompetitionForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                competition = form.save(commit=False)

                # ak máš v modeli pole created_by, nastav:
                if hasattr(competition, "created_by_id"):
                    competition.created_by = request.user

                competition.save()

                # vytvor membership organizátora
                # prispôsob názvy: CompetitionMembership, role field, enumy...
                CompetitionMembership.objects.get_or_create(
                    competition=competition,
                    user=request.user,
                    # defaults={"role": CompetitionMembership.Role.ORGANIZER},
                    defaults = {"role": "ORGANIZER"},
                )

            messages.success(request, "Súťaž bola vytvorená.")
            return redirect("competitions:my_competitions")
    else:
        form = CompetitionForm()

    return render(request, "competitions/competition_form.html", {"form": form})


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

    # Úlovky v súťaži (vidí každý člen súťaže)
    catches_qs = (
        Catch.objects
        .filter(competition=competition)
        .select_related("user")
        .order_by("caught_at", "created_at")
    )

    my_catches_qs = catches_qs.filter(user=request.user)

    context = {
        "competition": competition,
        "membership": membership,
        "status": _status_for_competition(competition),
        "is_organizer": bool(is_organizer),
        "is_contestant": bool(is_contestant),
        "catches": catches_qs,
        "my_catches": my_catches_qs,
    }
    return render(request, "competitions/detail.html", context)


@login_required
def competition_catch_list(request, pk: int):
    """HTMX partial: zoznam úlovkov v súťaži."""
    competition = get_object_or_404(Competition, pk=pk)

    membership = (
        CompetitionMembership.objects
        .filter(competition=competition, user=request.user)
        .first()
    )

    is_creator = (competition.created_by_id == request.user.id)
    if membership is None and not is_creator:
        raise Http404("Competition not found")

    is_organizer = is_creator or (membership and membership.role == CompetitionMembership.Role.ORGANIZER)

    catches_qs = (
        Catch.objects
        .filter(competition=competition)
        .select_related("user")
        .order_by("caught_at", "created_at")
    )

    return render(request, "competitions/_catch_list.html", {
        "competition": competition,
        "catches": catches_qs,
        "is_organizer": bool(is_organizer),
        "back_url": reverse("competitions:detail", kwargs={"pk": competition.pk}),
    })

@login_required
def invitations(request):
    organizer_competitions = _organizer_competitions_qs(request.user)

    # filter ?competition=ID (voliteľné)
    competition_id = request.GET.get("competition")
    filtered_competitions = organizer_competitions
    if competition_id:
        try:
            competition_id = int(competition_id)
            filtered_competitions = organizer_competitions.filter(id=competition_id)
        except ValueError:
            filtered_competitions = organizer_competitions

    if request.method == "POST":
        form = InvitationCreateForm(request.POST, competition_qs=organizer_competitions)
        if form.is_valid():
            invite = form.save()
            link = request.build_absolute_uri(
                reverse("competitions:invite_accept", kwargs={"token": str(invite.token)})
            )
            messages.success(request, f"Pozvánka vytvorená. Link: {link}")
            return redirect("competitions:invitations")
    else:
        form = InvitationCreateForm(competition_qs=organizer_competitions)

    inv_qs = (
        Invitation.objects
        .filter(competition__in=filtered_competitions)
        .select_related("competition", "invited_user")
        .order_by("-created_at")
    )

    now = timezone.now()
    items = []
    for inv in inv_qs:
        if inv.used_at:
            status = "Použitá"
        elif inv.expires_at and inv.expires_at < now:
            status = "Expirovaná"
        else:
            status = "Aktívna"

        link = request.build_absolute_uri(
            reverse("competitions:invite_accept", kwargs={"token": str(inv.token)})
        )

        items.append({
            "inv": inv,
            "competition": inv.competition,
            "email": inv.email,
            "invited_user": inv.invited_user,
            "created_at": inv.created_at,
            "expires_at": inv.expires_at,
            "used_at": inv.used_at,
            "status": status,
            "link": link,
        })

    return render(request, "competitions/invitations.html", {
        "form": form,
        "items": items,
        "competitions": organizer_competitions,
        "active_competition_id": int(competition_id) if str(competition_id).isdigit() else None,
    })

def invite_accept(request, token):
    invite = get_object_or_404(Invitation, token=token)

    # nech sa dá použiť aj keď user nie je prihlásený
    if not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path())

    if not invite.is_valid():
        messages.error(request, "Táto pozvánka je neplatná alebo už použitá.")
        return redirect("core:dashboard")

    # ak sa pozývalo emailom, skontrolujeme zhodu (MVP bezpečnosť)
    if invite.email and (request.user.email or "").lower() != invite.email.lower():
        messages.error(request, "Táto pozvánka je určená pre iný email.")
        return redirect("core:dashboard")

    with transaction.atomic():
        CompetitionMembership.objects.get_or_create(
            competition=invite.competition,
            user=request.user,
            defaults={"role": CompetitionMembership.Role.CONTESTANT},
        )

        # označ pozvánku ako použitú
        invite.invited_user = request.user
        invite.used_at = timezone.now()
        invite.save(update_fields=["invited_user", "used_at"])

    messages.success(request, f"Vstúpil si do súťaže: {invite.competition.name}")
    return redirect("competitions:detail", pk=invite.competition_id)

@login_required
def competition_my_catch_list(request, pk: int):
    """HTMX partial: úlovky prihláseného usera v konkrétnej súťaži."""
    competition = get_object_or_404(Competition, pk=pk)

    membership = (
        CompetitionMembership.objects
        .filter(competition=competition, user=request.user)
        .first()
    )

    is_creator = (competition.created_by_id == request.user.id)
    if membership is None and not is_creator:
        raise Http404("Competition not found")

    catches_qs = (
        Catch.objects
        .filter(competition=competition, user=request.user)
        .select_related("user")
        .order_by("-caught_at", "-created_at")
    )

    return render(request, "competitions/_my_catch_list.html", {
        "competition": competition,
        "catches": catches_qs,
        "back_url": reverse("competitions:detail", kwargs={"pk": competition.pk}),
    })
