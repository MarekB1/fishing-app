from __future__ import annotations

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

User = get_user_model()


class BootstrapFormMixin:
    """Doplnenie Bootstrap 5 tried do všetkých polí."""

    def _bootstrapify(self):
        for field in self.fields.values():
            w = field.widget
            existing = (w.attrs.get("class") or "").strip()

            if isinstance(w, forms.CheckboxInput):
                base = "form-check-input"
            elif isinstance(w, (forms.Select, forms.SelectMultiple)):
                base = "form-select"
            else:
                base = "form-control"

            w.attrs["class"] = (f"{existing} {base}").strip()


class EmailAuthenticationForm(BootstrapFormMixin, AuthenticationForm):
    """Login cez e-mail (field name ostáva `username`, aby sedel s LoginView)."""

    username = forms.EmailField(
        label="E-mail",
        widget=forms.EmailInput(attrs={
            "autocomplete": "email",
            "placeholder": "meno@priezvisko.com",
        }),
    )

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request=request, *args, **kwargs)

        if "password" in self.fields:
            self.fields["password"].label = "Heslo"
            self.fields["password"].widget.attrs["autocomplete"] = "current-password"

        self._bootstrapify()


class SignUpForm(BootstrapFormMixin, UserCreationForm):
    """Registrácia = všetko čo vidíš v profile + username (len pri registrácii)."""

    email = forms.EmailField(
        label="E-mailová adresa",
        required=True,
        widget=forms.EmailInput(attrs={
            "autocomplete": "email",
            "placeholder": "meno@priezvisko.com",
        }),
    )

    first_name = forms.CharField(
        label="Krstné meno",
        required=True,
        widget=forms.TextInput(attrs={"autocomplete": "given-name"}),
    )

    last_name = forms.CharField(
        label="Priezvisko",
        required=True,
        widget=forms.TextInput(attrs={"autocomplete": "family-name"}),
    )

    avatar = forms.ImageField(
        required=False, 
        label="Profilová fotka (nepovinné)"
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email", "password1", "password2")
        labels = {"username": "Používateľské meno"}
        widgets = {"username": forms.TextInput(attrs={"autocomplete": "username"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["password1"].label = "Heslo"
        self.fields["password2"].label = "Heslo (znovu)"
        self.fields["password1"].widget.attrs["autocomplete"] = "new-password"
        self.fields["password2"].widget.attrs["autocomplete"] = "new-password"

        self._bootstrapify()

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip()
        if not email:
            return email

        if User._default_manager.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "Tento e-mail je už používaný. Prihlás sa alebo použi iný e-mail."
            )
        return email

    def save(self, commit=True):
        user = super().save(commit=commit)
        
        avatar = self.cleaned_data.get('avatar')
        if avatar:
            user.profile.avatar = avatar
            if commit:
                user.profile.save()
                
        return user
