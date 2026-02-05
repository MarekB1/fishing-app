from django.contrib.auth import views as auth_views
from django.urls import path

from .views import EmailLoginView, SignUpView

urlpatterns = [
    # Auth
    path("login/", EmailLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    # Registration
    path("signup/", SignUpView.as_view(), name="signup"),

    # Password reset flow (používaš templates/registration/*)
    path("password_reset/", auth_views.PasswordResetView.as_view(), name="password_reset"),
    path("password_reset/done/", auth_views.PasswordResetDoneView.as_view(), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("reset/done/", auth_views.PasswordResetCompleteView.as_view(), name="password_reset_complete"),
]
