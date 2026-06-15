from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.urls import reverse

from apps.competitions.models import Competition, CompetitionMembership
from apps.notifications.models import Notification
from .models import Catch
from .forms import CatchCreateForm
from django.db.models import Q
from apps.competitions.scoring import build_scoreboard


def _ws_notify_user(user_id: int, *, unread_count: int, refresh_pending: bool = False):
    """
    Pošle WS event do group 'user_{id}'.
    Funguje až keď máš NotificationsConsumer napojený na túto group.
    """
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{user_id}",
        {
            "type": "notify",
            "data": {
                "unread_count": unread_count,
                "refresh_pending": bool(refresh_pending),
            },
        },
    )


@login_required
def catch_create(request):
    now = timezone.now()

    # user môže pridávať len do aktívnych súťaží, kde je CONTESTANT
    competition_qs = (
        Competition.objects
        .filter(
            starts_at__lte=now,
            ends_at__gte=now,
        )
        .filter(
            Q(
                memberships__user=request.user,
                memberships__role__in=[
                    CompetitionMembership.Role.CONTESTANT,
                ],
            )
            |
            Q(created_by=request.user)
        )
        .distinct()
        .order_by("starts_at")
    )

    has_competitions = competition_qs.exists()

    initial = {}
    cid = request.GET.get("competition")
    if cid and cid.isdigit():
        initial["competition"] = int(cid)

    if request.method == "POST":
        form = CatchCreateForm(request.POST, request.FILES, competition_qs=competition_qs)
        if form.is_valid():

            from datetime import timedelta
            recent_duplicate = Catch.objects.filter(
                user=request.user,
                competition=form.cleaned_data["competition"],
                created_at__gte=timezone.now() - timedelta(seconds=10)
            ).exists()

            if recent_duplicate:
                messages.info(request, "Úlovok sa už spracúva, prosím počkajte (ochrana proti viacnásobnému odoslaniu).")
                return redirect("competitions:detail", pk=form.cleaned_data["competition"].id)

            with transaction.atomic():
                catch = form.save(commit=False)
                catch.user = request.user
                catch.save()

                organizer_ids = set(
                    int(uid) for uid in CompetitionMembership.objects.filter(
                        competition=catch.competition,
                        is_organizer=True,
                    ).values_list("user_id", flat=True)
                )
                organizer_ids.add(int(catch.competition.created_by_id))

                for uid in organizer_ids:
                    Notification.objects.create(
                        competition=catch.competition,
                        recipient_id=uid,
                        type=Notification.Type.CATCH_CREATED,
                        payload={
                            "catch_id": catch.id,
                            "species": catch.species,
                            "contestant_id": request.user.id,
                        },
                    )

            # messages.success(request, "Úlovok bol pridaný a čaká na schválenie.")
            return redirect("competitions:detail", pk=catch.competition_id)
    else:
        form = CatchCreateForm(initial=initial, competition_qs=competition_qs)

    return render(request, "catches/catch_form.html", {"form": form, "has_competitions": has_competitions})


def _is_organizer(user, competition: Competition) -> bool:
    if competition.created_by_id == user.id:
        return True
    return CompetitionMembership.objects.filter(
        competition=competition,
        user=user,
        is_organizer=True,
    ).exists()


def _get_catch_for_organizer(user, pk: int) -> Catch:
    catch = get_object_or_404(
        Catch.objects.select_related("competition", "user"),
        pk=pk,
    )
    if not _is_organizer(user, catch.competition):
        raise Http404("Catch not found")
    return catch


def _get_catch_for_viewer(user, pk: int) -> tuple[Catch, bool]:
    """Vráti úlovok + info, či ho môže user moderovať (organizer/creator)."""
    catch = get_object_or_404(
        Catch.objects.select_related("competition", "user"),
        pk=pk,
    )

    competition = catch.competition
    is_creator = (competition.created_by_id == user.id)
    membership = CompetitionMembership.objects.filter(competition=competition, user=user).first()

    # do detailu pustíme len člena súťaže alebo tvorcu
    if membership is None and not is_creator:
        raise Http404("Catch not found")

    is_organizer = is_creator or (membership and membership.is_organizer)
    if is_organizer:
        return catch, True

    # člen súťaže bez organizer práv môže pozerať detail (bez moderovania)
    return catch, False


def _broadcast_pending_refresh(competition: Competition):
    """Refresh pending list + badge pre všetkých organizátorov danej súťaže."""
    organizer_ids = set(
        CompetitionMembership.objects.filter(
            competition=competition,
            is_organizer=True,
        ).values_list("user_id", flat=True)
    )
    organizer_ids.add(competition.created_by_id)

    for uid in organizer_ids:
        unread = Notification.objects.filter(recipient_id=uid, read_at__isnull=True).count()
        _ws_notify_user(uid, unread_count=unread, refresh_pending=True)


@login_required
def catch_detail(request, pk: int):
    catch, can_review = _get_catch_for_viewer(request.user, pk)
    back_url = request.GET.get("next") or reverse("competitions:detail", kwargs={"pk": catch.competition_id})
    return render(request, "catches/catch_detail.html", {
        "catch": catch,
        "can_review": bool(can_review),
        "back_url": back_url,
    })


@require_POST
@login_required
def catch_approve(request, pk: int):
    catch = _get_catch_for_organizer(request.user, pk)

    if catch.status != Catch.Status.PENDING:
        if request.headers.get("HX-Request") == "true":
            resp = HttpResponse("")
            resp["HX-Trigger"] = "pendingRefresh"
            return resp
        messages.info(request, "Úlovok už bol skontrolovaný.")
        return redirect(request.POST.get("next") or "notifications:pending")

    when = timezone.now()
    with transaction.atomic():
        temp_scores = build_scoreboard(
            approved_catches=[catch], 
            rules=catch.competition.scoring_rules
        )
        
        assigned_points = 0
        if temp_scores:
            assigned_points = temp_scores[0].points

        catch.status = Catch.Status.APPROVED
        catch.reviewed_by = request.user
        catch.reviewed_at = when
        catch.rejection_reason = ""
        catch.points = assigned_points  
        
        catch.save(update_fields=["status", "reviewed_by", "reviewed_at", "rejection_reason", "points"])

        Notification.objects.create(
            competition=catch.competition,
            recipient=catch.user,
            type=Notification.Type.CATCH_APPROVED,
            payload={"species": catch.species, "points": float(assigned_points)}
        )

        Notification.objects.filter(
            type=Notification.Type.CATCH_CREATED,
            payload__catch_id=catch.id,
            read_at__isnull=True,
        ).update(read_at=when)

        transaction.on_commit(lambda: _broadcast_pending_refresh(catch.competition))

    if request.headers.get("HX-Request") == "true":
        return HttpResponse("")

    messages.success(request, f"Úlovok bol schválený (získané body: {assigned_points}).")
    return redirect(request.POST.get("next") or "notifications:pending")


@require_POST
@login_required
def catch_reject(request, pk: int):
    catch = _get_catch_for_organizer(request.user, pk)

    if catch.status != Catch.Status.PENDING:
        if request.headers.get("HX-Request") == "true":
            resp = HttpResponse("")
            resp["HX-Trigger"] = "pendingRefresh"
            return resp
        messages.info(request, "Úlovok už bol skontrolovaný.")
        return redirect(request.POST.get("next") or "notifications:pending")

    reason = (request.POST.get("rejection_reason") or "").strip()
    if not reason:
        reason = (request.headers.get("HX-Prompt") or "").strip()

    when = timezone.now()
    with transaction.atomic():
        catch.status = Catch.Status.REJECTED
        catch.reviewed_by = request.user
        catch.reviewed_at = when
        catch.rejection_reason = reason
        catch.save(update_fields=["status", "reviewed_by", "reviewed_at", "rejection_reason"])

        Notification.objects.create(
            competition=catch.competition,
            recipient=catch.user,
            type=Notification.Type.CATCH_REJECTED,
            payload={"species": catch.species, "reason": reason}
        )

        Notification.objects.filter(
            type=Notification.Type.CATCH_CREATED,
            payload__catch_id=catch.id,
            read_at__isnull=True,
        ).update(read_at=when)

        transaction.on_commit(lambda: _broadcast_pending_refresh(catch.competition))

    if request.headers.get("HX-Request") == "true":
        return HttpResponse("")

    messages.success(request, "Úlovok bol odmietnutý.")
    return redirect(request.POST.get("next") or "notifications:pending")

@login_required
def my_catches(request):
    """Zoznam všetkých úlovkov prihláseného usera (voliteľne filtrované podľa súťaže)."""
    catches_qs = (
        Catch.objects
        .filter(user=request.user)
        .select_related("competition")
        .order_by("-caught_at", "-created_at")
    )

    active_competition_id = None
    competition_id = request.GET.get("competition")
    if competition_id and str(competition_id).isdigit():
        active_competition_id = int(competition_id)
        catches_qs = catches_qs.filter(competition_id=active_competition_id)

    competitions = (
        Competition.objects
        .filter(Q(memberships__user=request.user) | Q(created_by=request.user))
        .distinct()
        .order_by("-starts_at")
    )

    return render(request, "catches/my_catches.html", {
        "catches": catches_qs,
        "competitions": competitions,
        "active_competition_id": active_competition_id,
    })