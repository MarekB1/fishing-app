from django import forms
from django.utils import timezone
from .models import Invitation, Competition

DT_LOCAL_FORMAT = "%Y-%m-%dT%H:%M"

class CompetitionForm(forms.ModelForm):
    class Meta:
        model = Competition
        fields = [
            "tier",
            "name",
            "location_name",
            "fishing_spots_count",
            "allow_photos",
            "description",
            "starts_at",
            "ends_at",
        ]
        widgets = {
            "tier": forms.Select(),
            "name": forms.TextInput(attrs={"placeholder": "Názov súťaže"}),
            "location_name": forms.TextInput(attrs={"placeholder": "napr. Štrkovisko Zlaté piesky"}),
            "fishing_spots_count": forms.NumberInput(attrs={"min": "1", "step": "1"}),
            "allow_photos": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "starts_at": forms.DateTimeInput(format=DT_LOCAL_FORMAT, attrs={"type": "datetime-local"}),
            "ends_at": forms.DateTimeInput(format=DT_LOCAL_FORMAT, attrs={"type": "datetime-local"}),
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

        can_official = bool(
            user
            and getattr(user, "is_authenticated", False)
            and user.has_perm("competitions.can_create_official_competitions")
        )

        # bootstrap triedy
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault("class", "form-select")
            else:
                field.widget.attrs.setdefault("class", "form-control")

        # ak nemá permission, typ schováme a nútime UNOFFICIAL
        if not can_official:
            self.fields["tier"].widget = forms.HiddenInput()
            self.fields["tier"].initial = Competition.Tier.UNOFFICIAL

    def clean(self):
        cleaned = super().clean()
        starts_at = cleaned.get("starts_at")
        ends_at = cleaned.get("ends_at")

        if starts_at and ends_at and ends_at <= starts_at:
            self.add_error("ends_at", "Koniec musí byť po začiatku.")

        tier = cleaned.get("tier")
        can_official = bool(
            self.user
            and getattr(self.user, "is_authenticated", False)
            and self.user.has_perm("competitions.can_create_official_competitions")
        )
        if tier == Competition.Tier.OFFICIAL and not can_official:
            self.add_error("tier", "Nemáš oprávnenie vytvoriť oficiálnu súťaž.")

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
