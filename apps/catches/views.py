from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils import timezone

from apps.competitions.models import Competition, CompetitionMembership
from apps.notifications.models import Notification
from .forms import CatchCreateForm


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
        Competition.objects.filter(
            memberships__user=request.user,
            memberships__role=CompetitionMembership.Role.CONTESTANT,
            starts_at__lte=now,
            ends_at__gte=now,
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
            with transaction.atomic():
                catch = form.save(commit=False)
                catch.user = request.user
                catch.save()

                # organizátori = membership ORGANIZER + creator
                organizer_ids = set(
                    CompetitionMembership.objects.filter(
                        competition=catch.competition,
                        role=CompetitionMembership.Role.ORGANIZER,
                    ).values_list("user_id", flat=True)
                )
                organizer_ids.add(catch.competition.created_by_id)
                organizer_ids.discard(request.user.id)  # neposielať sám sebe

                # uložiť notifikácie
                # Notification.objects.bulk_create([
                #     Notification(
                #         competition=catch.competition,
                #         recipient_id=uid,
                #         type=Notification.Type.CATCH_CREATED,
                #         payload={
                #             "catch_id": catch.id,
                #             "species": catch.species,
                #             "contestant_id": request.user.id,
                #         },
                #     )
                #     for uid in organizer_ids
                # ])

                # WS až po commite (aby pending list videl catch v DB)
                def _after_commit():
                    for uid in organizer_ids:
                        unread = Notification.objects.filter(recipient_id=uid, read_at__isnull=True).count()
                        _ws_notify_user(uid, unread_count=unread, refresh_pending=True)

                transaction.on_commit(_after_commit)

            messages.success(request, "Úlovok bol pridaný a čaká na schválenie.")
            return redirect("competitions:detail", pk=catch.competition_id)
    else:
        form = CatchCreateForm(initial=initial, competition_qs=competition_qs)

    return render(request, "catches/catch_form.html", {"form": form, "has_competitions": has_competitions})
