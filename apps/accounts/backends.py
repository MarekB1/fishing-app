from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

UserModel = get_user_model()


class EmailBackend(ModelBackend):
    """
    Autentifikácia cez e-mail.

    Pozn.: Django LoginView/AuthForm posiela parameter `username`,
    takže tu ho interpretujeme ako e-mail.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        email = (kwargs.get("email") or username or "").strip()
        if not email or not password:
            return None

        qs = UserModel._default_manager.filter(email__iexact=email)

        # Ak je duplicitný email v DB, je to nejednoznačné -> radšej neautentifikovať
        if qs.count() != 1:
            return None

        user = qs.first()
        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None
