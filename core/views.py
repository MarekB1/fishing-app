from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

def home(request):
    if request.user.is_authenticated:
        return redirect("core:dashboard")
    return render(request, "core/home.html")

@login_required
def dashboard(request):
    return render(request, "core/dashboard.html")

@login_required
def profile(request):
    return render(request, "core/profile.html")
