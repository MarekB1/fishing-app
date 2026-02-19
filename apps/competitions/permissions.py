# apps/competitions/permissions.py

def user_is_premium(user) -> bool:
    """
    Premium = môže vytvárať OFFICIAL súťaže (a pod.).
    Legacy fallback: ak si mal pôvodný perm 'can_create_official_competitions'.
    """
    if not user or not getattr(user, "is_authenticated", False):
        return False

    return bool(
        user.has_perm("competitions.premium")
        or user.has_perm("competitions.can_create_official_competitions")  # legacy fallback
    )
