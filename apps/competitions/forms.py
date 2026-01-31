from django import forms
from django.utils import timezone
from .models import Invitation

from .models import Competition

DT_LOCAL_FORMAT = "%Y-%m-%dT%H:%M"

class CompetitionForm(forms.ModelForm):
    class Meta:
        model = Competition
        fields = ["name", "description", "starts_at", "ends_at"]
        widgets = {
            "starts_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "ends_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def clean(self):
        cleaned = super().clean()
        starts_at = cleaned.get("starts_at")
        ends_at = cleaned.get("ends_at")

        if starts_at and ends_at and ends_at <= starts_at:
            self.add_error("ends_at", "Koniec musí byť po začiatku.")

        # voliteľné MVP pravidlo: neumožniť minulosť
        # if starts_at and starts_at < timezone.now() - timezone.timedelta(minutes=1):
        #     self.add_error("starts_at", "Začiatok súťaže nemôže byť v minulosti.")

        return cleaned
    
class InvitationCreateForm(forms.ModelForm):
    class Meta:
        model = Invitation
        fields = ["competition", "email", "expires_at"]
        widgets = {
            "expires_at": forms.DateTimeInput(
                format=DT_LOCAL_FORMAT,
                attrs={"type": "datetime-local"},
            )
        }

    def __init__(self, *args, competition_qs=None, **kwargs):
        super().__init__(*args, **kwargs)
        if competition_qs is not None:
            self.fields["competition"].queryset = competition_qs

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip()
        if not email:
            raise forms.ValidationError("Zadaj email pozývaného.")
        return email

    def clean_expires_at(self):
        expires_at = self.cleaned_data.get("expires_at")
        if expires_at and expires_at <= timezone.now():
            raise forms.ValidationError("Expirácia musí byť v budúcnosti.")
        return expires_at    
