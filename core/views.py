from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from .forms import ProfileUpdateForm, BootstrapPasswordChangeForm


def home(request):
    if request.user.is_authenticated:
        return redirect("core:dashboard")
    return render(request, "core/home.html")


@login_required
def dashboard(request):
    return render(request, "core/dashboard.html", {
        "hide_nav_links_desktop": True,
    })



@login_required
def profile(request):
    user = request.user

    profile_form = ProfileUpdateForm(instance=user)
    password_form = BootstrapPasswordChangeForm(user=user)

    active_tab = "profile"

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "profile":
            profile_form = ProfileUpdateForm(request.POST, instance=user)
            active_tab = "profile"

            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Profil bol uložený.")
                return redirect("core:profile")
            else:
                messages.error(request, "Skontroluj formulár – niečo nie je vyplnené správne.")

        elif action == "password":
            password_form = BootstrapPasswordChangeForm(user=user, data=request.POST)
            active_tab = "password"

            if password_form.is_valid():
                updated_user = password_form.save()
                update_session_auth_hash(request, updated_user)  # aby ťa to neodhlásilo
                messages.success(request, "Heslo bolo zmenené.")
                return redirect("core:profile")
            else:
                messages.error(request, "Heslo sa nepodarilo zmeniť. Skontroluj chyby vo formulári.")

    return render(
        request,
        "core/profile.html",
        {
            "profile_form": profile_form,
            "password_form": password_form,
            "active_tab": active_tab,
        },
    )
