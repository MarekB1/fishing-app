from __future__ import annotations

import re

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST
from django.utils import timezone

from apps.notifications.models import Notification

from .models import Friendship

User = get_user_model()


def _tokenize(q: str) -> list[str]:
    q = (q or "").strip()
    if not q:
        return []
    # rozdeľ podľa whitespace; "Janko Mr" -> ["Janko", "Mr"]
    parts = re.split(r"\s+", q)
    return [p for p in parts if p]


def _build_search_q(tokens: list[str]) -> Q:
    # AND cez tokeny, OR cez polia
    qq = Q()
    for t in tokens:
        qq &= (
            Q(username__icontains=t)
            | Q(first_name__icontains=t)
            | Q(last_name__icontains=t)
        )
    return qq


@login_required
def friends_home(request):
    me = request.user

    accepted = (
        Friendship.objects
        .filter(status=Friendship.Status.ACCEPTED)
        .filter(Q(user_a=me) | Q(user_b=me))
        .select_related("user_a", "user_b", "requested_by")
        .order_by("-updated_at")
    )

    incoming = (
        Friendship.objects
        .filter(status=Friendship.Status.PENDING)
        .filter(Q(user_a=me) | Q(user_b=me))
        .exclude(requested_by=me)
        .select_related("user_a", "user_b", "requested_by")
        .order_by("-created_at")
    )

    outgoing = (
        Friendship.objects
        .filter(status=Friendship.Status.PENDING, requested_by=me)
        .filter(Q(user_a=me) | Q(user_b=me))
        .select_related("user_a", "user_b", "requested_by")
        .order_by("-created_at")
    )

    return render(request, "friends/friends.html", {
        "friends_accepted": accepted,
        "friends_incoming": incoming,
        "friends_outgoing": outgoing,
    })



@require_GET
@login_required
def lists_partial(request):
    return render(request, "friends/_lists.html", _lists_context(request.user))

@require_GET
@login_required
def user_search(request):
    me = request.user
    q = request.GET.get("q", "")
    tokens = _tokenize(q)

    if not tokens:
        return render(request, "friends/_search_results.html", {"results": [], "q": q})

    qs = (
        User.objects
        .filter(is_active=True)
        .exclude(id=me.id)
        .filter(_build_search_q(tokens))
        .order_by("first_name", "last_name", "username")
    )[:10]

    users = list(qs)
    user_ids = [u.id for u in users]

    # vzťahy medzi me a users (len relevantné stavy)
    rels = Friendship.objects.filter(
        Q(user_a_id=me.id, user_b_id__in=user_ids) | Q(user_b_id=me.id, user_a_id__in=user_ids)
    ).select_related("requested_by")

    rel_by_other_id = {}
    for fr in rels:
        other = fr.other_user(me)
        rel_by_other_id[other.id] = fr

    results = []
    for u in users:
        fr = rel_by_other_id.get(u.id)
        state = "none"
        if fr:
            if fr.status == Friendship.Status.ACCEPTED:
                state = "friend"
            elif fr.status == Friendship.Status.PENDING:
                state = "incoming" if fr.requested_by_id != me.id else "outgoing"
            else:
                state = "declined"
        results.append({"user": u, "state": state, "friendship": fr})

    return render(request, "friends/_search_results.html", {"results": results, "q": q})


@require_POST
@login_required
@transaction.atomic
def send_request(request, user_id: int):
    me = request.user
    other = get_object_or_404(User, pk=user_id, is_active=True)

    if other.id == me.id:
        return HttpResponseBadRequest("Nemôžeš pridať sám seba.")

    a_id, b_id = sorted([me.id, other.id])

    fr, created = Friendship.objects.select_for_update().get_or_create(
        user_a_id=a_id,
        user_b_id=b_id,
        defaults={"requested_by": me, "status": Friendship.Status.PENDING},
    )

    if not created:
        if fr.status == Friendship.Status.ACCEPTED:
            messages.info(request, "Už ste priatelia.")
        elif fr.status == Friendship.Status.PENDING:
            if fr.requested_by_id == me.id:
                messages.info(request, "Žiadosť už bola odoslaná.")
            else:
                fr.mark_accepted()
                # messages.success(request, "Žiadosť bola prijatá. Ste priatelia.")
        else:
            fr.requested_by = me
            fr.status = Friendship.Status.PENDING
            fr.responded_at = None
            fr.save(update_fields=["requested_by", "status", "responded_at", "updated_at"])
            # messages.success(request, "Žiadosť bola odoslaná.")
    # else:
    #     messages.success(request, "Žiadosť bola odoslaná.")

    Notification.objects.create(
        recipient=other,
        type=Notification.Type.FRIEND_REQUEST,
        payload={"sender_name": me.get_full_name() or me.username}
    )

    if request.htmx:
        fr.refresh_from_db()
        
        if fr.status == Friendship.Status.ACCEPTED:
            state = "friend"
        elif fr.status == Friendship.Status.PENDING:
            state = "incoming" if fr.requested_by_id != me.id else "outgoing"
        else:
            state = "declined"

        response = render(request, "friends/_search_result_row.html", {
            "u": other,
            "state": state,
            "friendship": fr,
        })
        response["HX-Trigger"] = "friendsRefresh"
        return response

    return redirect("friends:home")


@require_POST
@login_required
@transaction.atomic
def accept_request(request, friendship_id: int):
    me = request.user
    fr = get_object_or_404(
        Friendship.objects.select_for_update(),
        pk=friendship_id,
    )

    if fr.status != Friendship.Status.PENDING:
        return HttpResponseBadRequest("Nie je pending.")

    if me.id not in (fr.user_a_id, fr.user_b_id):
        return HttpResponseBadRequest("Nemáš prístup.")

    if fr.requested_by_id == me.id:
        return HttpResponseBadRequest("Toto je tvoja odoslaná žiadosť.")

    fr.mark_accepted()
    # messages.success(request, "Priateľstvo bolo potvrdené.")

    Notification.objects.create(
        recipient=fr.requested_by,
        type=Notification.Type.FRIEND_ACCEPTED,
        payload={"sender_name": me.get_full_name() or me.username}
    )

    if request.htmx:
        return render(request, "friends/_lists.html", _lists_context(me))
    return redirect("friends:home")


@require_POST
@login_required
@transaction.atomic
def decline_request(request, friendship_id: int):
    me = request.user
    fr = get_object_or_404(
        Friendship.objects.select_for_update(),
        pk=friendship_id,
    )

    if fr.status != Friendship.Status.PENDING:
        return HttpResponseBadRequest("Nie je pending.")

    if me.id not in (fr.user_a_id, fr.user_b_id):
        return HttpResponseBadRequest("Nemáš prístup.")

    if fr.requested_by_id == me.id:
        return HttpResponseBadRequest("Toto je tvoja odoslaná žiadosť.")

    fr.mark_declined()
    # messages.info(request, "Žiadosť bola zamietnutá.")

    if request.htmx:
        return render(request, "friends/_lists.html", _lists_context(me))
    return redirect("friends:home")


@require_POST
@login_required
@transaction.atomic
def remove_friend(request, friendship_id: int):
    me = request.user
    fr = get_object_or_404(
        Friendship.objects.select_for_update(),
        pk=friendship_id,
    )

    if me.id not in (fr.user_a_id, fr.user_b_id):
        return HttpResponseBadRequest("Nemáš prístup.")

    fr.status = Friendship.Status.DECLINED
    fr.responded_at = timezone.now()
    fr.save(update_fields=["status", "responded_at", "updated_at"])
    # messages.info(request, "Priateľ bol odstránený.")

    if request.htmx:
        return render(request, "friends/_lists.html", _lists_context(me))
    return redirect("friends:home")


def _lists_context(me):
    accepted = (
        Friendship.objects
        .filter(status=Friendship.Status.ACCEPTED)
        .filter(Q(user_a=me) | Q(user_b=me))
        .select_related("user_a", "user_b", "requested_by")
        .order_by("-updated_at")
    )

    incoming = (
        Friendship.objects
        .filter(status=Friendship.Status.PENDING)
        .filter(Q(user_a=me) | Q(user_b=me))
        .exclude(requested_by=me)
        .select_related("user_a", "user_b", "requested_by")
        .order_by("-created_at")
    )

    outgoing = (
        Friendship.objects
        .filter(status=Friendship.Status.PENDING, requested_by=me)
        .filter(Q(user_a=me) | Q(user_b=me))
        .select_related("user_a", "user_b", "requested_by")
        .order_by("-created_at")
    )

    return {
        "friends_accepted": accepted,
        "friends_incoming": incoming,
        "friends_outgoing": outgoing,
    }
