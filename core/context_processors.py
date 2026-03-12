from django.db.models import Count
from apps.competitions.permissions import user_is_premium


def nav_user_roles(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}

    is_premium = user_is_premium(user)

    try:
        from apps.competitions.models import Competition, CompetitionMembership

        organizer_comp_ids = set(
            Competition.objects.filter(created_by=user).values_list("id", flat=True)
        )
        organizer_comp_ids |= set(
            CompetitionMembership.objects.filter(
                user=user,
                is_organizer=True,
            ).values_list("competition_id", flat=True)
        )

        is_organizer = bool(organizer_comp_ids)

        missing = []
        missing_total = 0

        if organizer_comp_ids:
            qs = (
                CompetitionMembership.objects
                .filter(
                    competition_id__in=organizer_comp_ids,
                    role=CompetitionMembership.Role.CONTESTANT,
                    spot_number__isnull=True,
                )
                .values("competition_id", "competition__name")
                .annotate(count=Count("id"))
                .order_by("-count", "competition__name")
            )
            missing = [
                {
                    "competition_id": row["competition_id"],
                    "competition_name": row["competition__name"],
                    "count": row["count"],
                }
                for row in qs
            ]
            missing_total = sum(row["count"] for row in qs)

    except Exception:
        is_organizer = False
        missing_total = 0
        missing = []

    return {
        "nav_is_organizer": is_organizer,
        "nav_is_premium": is_premium,
        "nav_missing_spots_total": missing_total,
        "nav_missing_spots": missing,
    }