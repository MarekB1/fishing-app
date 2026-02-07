import io
import re

from django.contrib.auth import get_user_model
from django.views.decorators.http import require_GET, require_POST
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.shortcuts import redirect, render
from django.db import transaction
from django.db.models import Q
from django.urls import reverse
from django.db import IntegrityError


from .forms import CompetitionForm
from .models import Competition, CompetitionMembership, Invitation, InvitationUse
from .forms import InvitationCreateForm
from apps.catches.models import Catch
from django.contrib.auth.views import redirect_to_login
from apps.friends.models import Friendship


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

UNOFFICIAL_MAX_CONTESTANTS = 5

def _unofficial_limit_reached(competition: Competition) -> bool:
    if competition.is_official:
        return False
    return (
        CompetitionMembership.objects
        .filter(competition=competition, role=CompetitionMembership.Role.CONTESTANT)
        .count()
        >= UNOFFICIAL_MAX_CONTESTANTS
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
    can_create_official = request.user.has_perm("competitions.can_create_official_competitions")

    if request.method == "POST":
        form = CompetitionForm(request.POST, user=request.user)
        if form.is_valid():
            with transaction.atomic():
                competition = form.save(commit=False)
                if hasattr(competition, "created_by_id"):
                    competition.created_by = request.user
                competition.save()

                CompetitionMembership.objects.get_or_create(
                    competition=competition,
                    user=request.user,
                    defaults={"role": "ORGANIZER"},
                )

            messages.success(request, "Súťaž bola vytvorená.")
            return redirect("competitions:my_competitions")
    else:
        form = CompetitionForm(user=request.user)

    return render(request, "competitions/competition_form.html", {
        "form": form,
        "can_create_official": can_create_official,
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

    # Úlovky v súťaži (vidí každý člen súťaže)
    catches_qs = (
        Catch.objects
        .filter(competition=competition)
        .select_related("user")
        .order_by("caught_at", "created_at")
    )

    my_catches_qs = catches_qs.filter(user=request.user)

    contestant_memberships = []
    spots_range = range(1, competition.fishing_spots_count + 1)
    if is_organizer:
        contestant_memberships = (
            CompetitionMembership.objects
            .filter(competition=competition, role=CompetitionMembership.Role.CONTESTANT)
            .select_related("user")
            .order_by("spot_number", "user__username")
        )

    context = {
        "competition": competition,
        "membership": membership,
        "status": _status_for_competition(competition),
        "is_organizer": bool(is_organizer),
        "is_contestant": bool(is_contestant),
        "catches": catches_qs,
        "my_catches": my_catches_qs,
        "contestant_memberships": contestant_memberships,
        "spots_range": spots_range,
    }
    return render(request, "competitions/detail.html", context)

@require_POST
@login_required
@transaction.atomic
def membership_set_spot(request, pk: int, membership_id: int):
    competition = get_object_or_404(Competition, pk=pk)
    _require_organizer_or_404(request.user, competition)

    m = get_object_or_404(
        CompetitionMembership.objects.select_related("user"),
        pk=membership_id,
        competition=competition,
        role=CompetitionMembership.Role.CONTESTANT,
    )

    spots_range = range(1, competition.fishing_spots_count + 1)
    raw = (request.POST.get("spot_number") or "").strip()
    error = None

    if raw == "":
        spot = None  # vymazanie priradenia
    else:
        if not raw.isdigit():
            error = "Zadaj číslo."
            spot = m.spot_number
        else:
            spot = int(raw)

            if spot < 1 or spot > competition.fishing_spots_count:
                error = f"Povolené je 1 až {competition.fishing_spots_count}."
            elif CompetitionMembership.objects.filter(
                competition=competition,
                spot_number=spot,
            ).exclude(pk=m.pk).exists():
                error = f"Miesto {spot} je už obsadené."

    if error:
        return render(request, "competitions/_member_row.html", {
            "competition": competition,
            "m": m,
            "error": error,
            "spots_range": spots_range,
        })

    m.spot_number = spot

    if spot < 1 or spot > competition.fishing_spots_count:
        error = f"Povolené je 1 až {competition.fishing_spots_count}."

    try:
        m.save(update_fields=["spot_number"])
    except IntegrityError:
        # safety net pri race condition
        return render(request, "competitions/_member_row.html", {
            "competition": competition,
            "m": m,
            "error": "Toto miesto je už obsadené.",
            "spots_range": spots_range,
        })

    return render(request, "competitions/_member_row.html", {
        "competition": competition,
        "m": m,
        "error": None,
        "spots_range": spots_range,
    })

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

    if competition.is_official and not is_organizer:
        raise Http404("Competition not found")


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
    competition_id_raw = request.GET.get("competition")
    active_competition_id = None
    filtered_competitions = organizer_competitions

    if competition_id_raw:
        try:
            active_competition_id = int(competition_id_raw)
            filtered_competitions = organizer_competitions.filter(id=active_competition_id)
        except ValueError:
            active_competition_id = None
            filtered_competitions = organizer_competitions

    # POST: vytvorenie klasickej email pozvánky
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

    # --- NEW: selected_competition + share_invite + share_link (pre zdieľateľný link/QR) ---
    selected_competition = (
        organizer_competitions.filter(id=active_competition_id).first()
        if active_competition_id else None
    )

    share_invite = None
    share_link = None

    # Guard: ak model Invitation ešte nemá "kind"
    try:
        Invitation._meta.get_field("kind")
        kind_link_value = Invitation.Kind.LINK
    except Exception:
        kind_link_value = None

    if selected_competition and kind_link_value:
        share_invite = Invitation.objects.filter(
            competition=selected_competition,
            kind=kind_link_value,
        ).first()

        if share_invite:
            share_link = request.build_absolute_uri(
                reverse("competitions:invite_accept", kwargs={"token": str(share_invite.token)})
            )

    return render(request, "competitions/invitations.html", {
        "form": form,
        "items": items,
        "competitions": organizer_competitions,
        "active_competition_id": active_competition_id,

        # NEW:
        "selected_competition": selected_competition,
        "share_invite": share_invite,
        "share_link": share_link,
    })


    
def invite_accept(request, token):
    invite = get_object_or_404(Invitation, token=token)

    # nech sa dá použiť aj keď user nie je prihlásený
    if not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path())

    # rýchla kontrola
    if not invite.is_valid():
        messages.error(request, "Táto pozvánka je neplatná alebo už nie je použiteľná.")
        return redirect("core:dashboard")

    # DIRECT email bezpečnosť
    if invite.kind == Invitation.Kind.DIRECT:
        if invite.email and (request.user.email or "").lower() != invite.email.lower():
            messages.error(request, "Táto pozvánka je určená pre iný email.")
            return redirect("core:dashboard")

    with transaction.atomic():
        # zamkneme invite pri LINK aby sme korektne riešili max_uses
        invite = Invitation.objects.select_for_update().get(pk=invite.pk)

        if not invite.is_valid():
            messages.error(request, "Táto pozvánka už nie je použiteľná.")
            return redirect("core:dashboard")
        
        competition = invite.competition

        already_member = CompetitionMembership.objects.filter(
            competition=competition,
            user=request.user,
        ).exists()

        if (not already_member) and _unofficial_limit_reached(competition):
            messages.error(request, "Táto neoficiálna súťaž už má maximum 5 účastníkov.")
            return redirect("core:dashboard")

        CompetitionMembership.objects.get_or_create(
            competition=invite.competition,
            user=request.user,
            defaults={"role": CompetitionMembership.Role.CONTESTANT},
        )

        if invite.kind == Invitation.Kind.DIRECT:
            invite.invited_user = request.user
            invite.used_at = timezone.now()
            invite.save(update_fields=["invited_user", "used_at"])

        else:
            # LINK: 1x per user + increment uses_count iba pri prvom použití
            use, created = InvitationUse.objects.get_or_create(
                invitation=invite,
                user=request.user,
            )
            if created:
                invite.uses_count += 1
                invite.save(update_fields=["uses_count"])
            else:
                messages.info(request, "Túto pozvánku si už použil. Si už v súťaži.")

    messages.success(request, f"Vstúpil si do súťaže: {invite.competition.name}")
    return redirect("competitions:detail", pk=invite.competition_id)

@require_POST
@login_required
def invite_link_create(request):
    competition_id = request.POST.get("competition_id")
    if not competition_id or not str(competition_id).isdigit():
        return HttpResponseBadRequest("Missing competition_id")

    competition = get_object_or_404(Competition, pk=int(competition_id))
    _require_organizer_or_404(request.user, competition)

    invite, _created = Invitation.objects.get_or_create(
        competition=competition,
        kind=Invitation.Kind.LINK,
        defaults={"created_by": request.user},
    )

    link = request.build_absolute_uri(
        reverse("competitions:invite_accept", kwargs={"token": str(invite.token)})
    )

    return render(request, "competitions/_invite_link_card.html", {
        "selected_competition": competition,
        "share_invite": invite,
        "share_link": link,
    })

def invite_qr(request, token):
    invite = get_object_or_404(Invitation, token=token, kind=Invitation.Kind.LINK)

    url = request.build_absolute_uri(
        reverse("competitions:invite_accept", kwargs={"token": str(invite.token)})
    )

    try:
        import qrcode
    except ImportError:
        raise Http404("QR dependency missing (pip install qrcode[pil])")

    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    resp = HttpResponse(buf.getvalue(), content_type="image/png")
    if request.GET.get("download") == "1":
        resp["Content-Disposition"] = f'attachment; filename="competition-invite-{invite.competition_id}.png"'
    return resp

@require_GET
@login_required
def invite_user_search(request):
    competition_id = request.GET.get("competition_id")
    q = request.GET.get("q", "")
    friends_only = request.GET.get("friends_only") == "1"

    if not competition_id or not str(competition_id).isdigit():
        return HttpResponseBadRequest("Missing competition_id")

    competition = get_object_or_404(Competition, pk=int(competition_id))
    _require_organizer_or_404(request.user, competition)

    tokens = _tokenize(q)
    if not tokens:
        limit_reached = _unofficial_limit_reached(competition)
        return render(request, "competitions/_invite_user_search_results.html", {
            "results": [],
            "q": q,
            "competition": competition,
            "limit_reached": limit_reached,
        })

    qs = (
        User.objects
        .filter(is_active=True)
        .exclude(id=request.user.id)
        .filter(_build_search_q(tokens))
        .order_by("first_name", "last_name", "username")
    )

    users = list(qs[:10])
    user_ids = [u.id for u in users]

    # kto je už člen súťaže
    member_ids = set(
        CompetitionMembership.objects
        .filter(competition=competition, user_id__in=user_ids)
        .values_list("user_id", flat=True)
    )

    # kto je priateľ
    friend_ids = set()
    fr_qs = (
        Friendship.objects
        .filter(status=Friendship.Status.ACCEPTED)
        .filter(
            Q(user_a_id=request.user.id, user_b_id__in=user_ids)
            | Q(user_b_id=request.user.id, user_a_id__in=user_ids)
        )
        .select_related("user_a", "user_b")
    )
    for fr in fr_qs:
        other = fr.other_user(request.user)
        friend_ids.add(other.id)

    if friends_only:
        users = [u for u in users if u.id in friend_ids]

    results = []
    for u in users:
        results.append({
            "user": u,
            "is_member": u.id in member_ids,
            "is_friend": u.id in friend_ids,
        })

    return render(request, "competitions/_invite_user_search_results.html", {
        "results": results,
        "q": q,
        "competition": competition,
    })

@require_POST
@login_required
@transaction.atomic
def invite_user_add(request, user_id: int):
    competition_id = request.POST.get("competition_id")
    if not competition_id or not str(competition_id).isdigit():
        return HttpResponseBadRequest("Missing competition_id")

    competition = get_object_or_404(Competition, pk=int(competition_id))
    _require_organizer_or_404(request.user, competition)

    # ✅ najprv si načítaj "other" – používame ho nižšie
    other = get_object_or_404(User, pk=user_id, is_active=True)

    # zistíme či je friend (na badge) – len raz
    is_friend = Friendship.objects.filter(
        status=Friendship.Status.ACCEPTED
    ).filter(
        Friendship.pair_q(request.user.id, other.id)
    ).exists()

    # je už člen?
    already_member = CompetitionMembership.objects.filter(
        competition=competition,
        user=other,
    ).exists()

    if already_member:
        return render(request, "competitions/_invite_user_row.html", {
            "competition": competition,
            "u": other,
            "is_member": True,
            "is_friend": is_friend,
            "limit_reached": False,
        })

    # ✅ ak je limit (iba neoficiálna) a user ešte nie je člen → blok
    if _unofficial_limit_reached(competition):
        return render(request, "competitions/_invite_user_row.html", {
            "competition": competition,
            "u": other,
            "is_member": False,
            "is_friend": is_friend,
            "limit_reached": True,
        })

    # inak pridaj člena
    CompetitionMembership.objects.get_or_create(
        competition=competition,
        user=other,
        defaults={"role": CompetitionMembership.Role.CONTESTANT},
    )

    return render(request, "competitions/_invite_user_row.html", {
        "competition": competition,
        "u": other,
        "is_member": True,
        "is_friend": is_friend,
        "limit_reached": False,
    })

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

User = get_user_model()

def _require_organizer_or_404(user, competition: Competition):
    membership = (
        CompetitionMembership.objects
        .filter(competition=competition, user=user)
        .first()
    )
    is_creator = (competition.created_by_id == user.id)
    is_organizer = is_creator or (membership and membership.role == CompetitionMembership.Role.ORGANIZER)
    if not is_organizer:
        raise Http404("Competition not found")


def _tokenize(q: str) -> list[str]:
    q = (q or "").strip()
    if not q:
        return []
    parts = re.split(r"\s+", q)
    return [p for p in parts if p]


def _build_search_q(tokens: list[str]):
    qq = Q()
    for t in tokens:
        qq &= (
            Q(username__icontains=t)
            | Q(first_name__icontains=t)
            | Q(last_name__icontains=t)
        )
    return qq
