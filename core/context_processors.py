from django.utils import timezone
from django.db.models import Count, Q

# core/context_processors.py
def nav_user_roles(request):
    """
    Navbar helper:
    - nav_is_organizer: True ak je user tvorca aspoň 1 súťaže alebo má membership rolu ORGANIZER
    - nav_missing_spots_total / nav_missing_spots: počet účastníkov bez lovného miesta (pre organizátora)
    """
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}

    try:
        from apps.competitions.models import Competition, CompetitionMembership

        organizer_comp_ids = set(
            Competition.objects.filter(created_by=user).values_list("id", flat=True)
        )
        organizer_comp_ids |= set(
            CompetitionMembership.objects.filter(
                user=user,
                role=CompetitionMembership.Role.ORGANIZER,
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
        "nav_missing_spots_total": missing_total,
        "nav_missing_spots": missing,
    }