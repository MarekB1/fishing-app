from django.utils import timezone

# core/context_processors.py
def nav_user_roles(request):
    """
    Navbar helper:
    - nav_is_organizer: True ak je user tvorca aspoň 1 súťaže alebo má membership rolu ORGANIZER
    (bez ohľadu na to, či súťaž práve beží).
    """
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}

    try:
        from apps.competitions.models import Competition, CompetitionMembership

        is_creator = Competition.objects.filter(created_by=user).exists()
        is_member_organizer = CompetitionMembership.objects.filter(
            user=user,
            role=CompetitionMembership.Role.ORGANIZER,
        ).exists()

        is_organizer = bool(is_creator or is_member_organizer)
    except Exception:
        is_organizer = False

    return {
        "nav_is_organizer": is_organizer,
    }

