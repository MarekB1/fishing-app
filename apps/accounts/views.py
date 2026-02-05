from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import FormView

from .forms import EmailAuthenticationForm, SignUpForm


class EmailLoginView(auth_views.LoginView):
    template_name = "registration/login.html"
    authentication_form = EmailAuthenticationForm
    redirect_authenticated_user = True


class SignUpView(FormView):
    template_name = "registration/signup.html"
    form_class = SignUpForm
    success_url = reverse_lazy("core:dashboard")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("core:dashboard")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.save()

        raw_password = form.cleaned_data["password1"]
        authed = authenticate(self.request, email=user.email, password=raw_password)
        if authed is not None:
            auth_login(self.request, authed)
        else:
            # fallback: ak by authenticate zlyhalo, tak aspoň nech to nespadne
            auth_login(self.request, user, backend="django.contrib.auth.backends.ModelBackend")

        messages.success(self.request, "Účet bol vytvorený. Si prihlásený.")
        return super().form_valid(form)
