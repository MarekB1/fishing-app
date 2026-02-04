from django.utils import timezone

def nav_user_roles(request):
    """
    Navbar helper:
    - Contestant: vždy (ak je prihlásený)
    - Organizer: ak má aspoň 1 aktívnu súťaž, ktorú vytvoril / organizuje
    """
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}

    now = timezone.now()

    # --- VARIANTA A (najčastejšie): Competition má FK na usera (created_by alebo organizer)
    # UPRAV SI NÁZVY POLÍ PODĽA TVOJHO MODELU:
    # - organizer / created_by
    # - starts_at / ends_at (alebo start_at / end_at)
    try:
        from apps.competitions.models import Competition
        is_organizer = Competition.objects.filter(
            created_by=user,          # ← zmeň na organizer=user, ak tak máš model
            starts_at__lte=now,       # ← zmeň názov poľa podľa seba
            ends_at__gte=now,         # ← zmeň názov poľa podľa seba
        ).exists()
    except Exception:
        is_organizer = False

    # --- VARIANTA B (ak používaš CompetitionMembership s rolami)
    # Ak toto používaš, tak hore VARIANTU A pokojne vyhoď a nechaj iba toto:
    # from apps.competitions.models import CompetitionMembership
    # is_organizer = CompetitionMembership.objects.filter(
    #     user=user,
    #     role="ORGANIZER",
    #     competition__starts_at__lte=now,
    #     competition__ends_at__gte=now,
    # ).exists()

    roles = ["Contestant"]
    if is_organizer:
        roles.append("Organizer")

    return {
        # "nav_roles_text": " / ".join(roles),  # "Contestant / Organizer"
        "nav_is_organizer": is_organizer,
    }
