from django import forms
from django.utils import timezone

from .models import Catch

DT_LOCAL_FORMAT = "%Y-%m-%dT%H:%M"


class CatchCreateForm(forms.ModelForm):
    class Meta:
        model = Catch
        fields = ["competition", "species", "length_cm", "weight_kg", "caught_at", "note", "photo"]
        widgets = {
            "caught_at": forms.DateTimeInput(format=DT_LOCAL_FORMAT, attrs={"type": "datetime-local"}),
            "note": forms.Textarea(attrs={"rows": 3}),
            "length_cm": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "weight_kg": forms.NumberInput(attrs={"step": "0.001", "min": "0"}),
            "photo": forms.ClearableFileInput(attrs={"accept": "image/*"}),
        }

    def __init__(self, *args, competition_qs=None, **kwargs):
        super().__init__(*args, **kwargs)
        if competition_qs is not None:
            self.fields["competition"].queryset = competition_qs

    def clean_photo(self):
        photo = self.cleaned_data.get("photo")
        if not photo:
            return photo  # ✅ už nie je povinná

        max_mb = 8
        if photo.size > max_mb * 1024 * 1024:
            raise forms.ValidationError(f"Fotka je príliš veľká (max {max_mb}MB).")

        allowed = {"image/jpeg", "image/png", "image/webp"}
        content_type = getattr(photo, "content_type", None)
        if content_type and content_type not in allowed:
            raise forms.ValidationError("Povolené sú iba JPG, PNG alebo WEBP.")

        return photo


    def clean(self):
        cleaned = super().clean()
        competition = cleaned.get("competition")
        caught_at = cleaned.get("caught_at")
        photo = cleaned.get("photo")

        length_cm = cleaned.get("length_cm")
        weight_kg = cleaned.get("weight_kg")

        if competition and not getattr(competition, "allow_photos", True) and photo:
            self.add_error("photo", "Táto súťaž nepovoľuje pridávanie fotiek.")

        if length_cm is not None and length_cm <= 0:
            self.add_error("length_cm", "Dĺžka musí byť väčšia ako 0.")
        if weight_kg is not None and weight_kg <= 0:
            self.add_error("weight_kg", "Váha musí byť väčšia ako 0.")

        if competition and caught_at:
            if not (competition.starts_at <= caught_at <= competition.ends_at):
                self.add_error("caught_at", "Čas úlovku musí byť v rámci trvania súťaže.")

        return cleaned
