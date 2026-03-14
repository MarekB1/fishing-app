# apps/competitions/forms.py
from decimal import Decimal

from django import forms
from django.utils import timezone

from .permissions import user_is_premium
from apps.catches.constants import FISH_SPECIES
from .models import Invitation, Competition
from .scoring import (
    SCORING_MODE_CHOICES,
    TIE_BREAKER_CHOICES,
    COMBO_COMPONENT_CHOICES,
    ScoringMode,
    TieBreakerPreset,
    normalize_rules,
    parse_species_points,
)

DT_LOCAL_FORMAT = "%Y-%m-%dT%H:%M"


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
        # Nastaví queryset pre competition field a Bootstrap triedy pre widgety.
        super().__init__(*args, **kwargs)
        if competition_qs is not None:
            self.fields["competition"].queryset = competition_qs

        self.fields["competition"].widget.attrs.setdefault("class", "form-select")
        self.fields["email"].widget.attrs.setdefault("class", "form-control")
        self.fields["expires_at"].widget.attrs.setdefault("class", "form-control")

    def clean_email(self):
        # Vyčistí a validuje email pozývaného používateľa.
        email = (self.cleaned_data.get("email") or "").strip()
        if not email:
            raise forms.ValidationError("Zadaj email pozývaného.")
        return email

    def clean_expires_at(self):
        # Skontroluje, že expirácia pozvánky je v budúcnosti.
        expires_at = self.cleaned_data.get("expires_at")
        if expires_at and expires_at <= timezone.now():
            raise forms.ValidationError("Expirácia musí byť v budúcnosti.")
        return expires_at


class CompetitionForm(forms.ModelForm):
    # Výber hlavného bodovacieho režimu.
    scoring_mode = forms.ChoiceField(
        choices=SCORING_MODE_CHOICES,
        initial=ScoringMode.COUNT,
        label="Bodovanie",
    )

    # Výber pravidla pre riešenie remízy.
    tie_breaker_preset = forms.ChoiceField(
        choices=TIE_BREAKER_CHOICES,
        initial=TieBreakerPreset.AUTO,
        label="Riešenie remízy",
        help_text="Použije sa, ak majú dvaja súťažiaci rovnaký počet bodov.",
    )

    # COUNT
    count_points_per_catch = forms.IntegerField(
        required=False,
        min_value=0,
        initial=10,
        label="Body za úlovok",
        help_text="Napr. 10 = každý schválený úlovok má +10 bodov.",
    )

    # LENGTH modes
    length_points_per_cm = forms.DecimalField(
        required=False,
        min_value=Decimal("0"),
        max_digits=10,
        decimal_places=3,
        initial=Decimal("1"),
        label="Body za 1 cm",
        help_text="Napr. 1 = 1 bod za 1 cm.",
    )

    # WEIGHT mode
    weight_points_per_kg = forms.DecimalField(
        required=False,
        min_value=Decimal("0"),
        max_digits=10,
        decimal_places=3,
        initial=Decimal("10"),
        label="Body za 1 kg",
        help_text="Napr. 10 = 10 bodov za 1 kg.",
    )

    # SPECIES_TABLE
    species_points_text = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 5,
                "placeholder": "Kapor=50\nŠťuka=80\nZubáč=70",
            }
        ),
        label="Tabuľka bodov podľa druhu",
        help_text="Jeden druh na riadok. Separátor môže byť = alebo : alebo ;",
    )

    species_default_points = forms.IntegerField(
        required=False,
        min_value=0,
        initial=0,
        label="Default body (ak druh nie je v tabuľke)",
    )

    # COMBO
    combo_selected_modes = forms.MultipleChoiceField(
        required=False,
        choices=COMBO_COMPONENT_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        label="Systémy v kombinovanom bodovaní",
        help_text="Vyber aspoň 2 systémy. Ich výsledné body sa spočítajú.",
    )

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
            "starts_at": forms.DateTimeInput(
                format=DT_LOCAL_FORMAT,
                attrs={"type": "datetime-local"},
            ),
            "ends_at": forms.DateTimeInput(
                format=DT_LOCAL_FORMAT,
                attrs={"type": "datetime-local"},
            ),
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, user=None, **kwargs):
        # Inicializuje formulár, nastaví práva a predvyplní scoring polia z JSON pravidiel.
        self.user = user
        super().__init__(*args, **kwargs)

        can_official = user_is_premium(user)

        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(field.widget, forms.CheckboxSelectMultiple):
                field.widget.attrs.setdefault("class", "")
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault("class", "form-select")
            else:
                field.widget.attrs.setdefault("class", "form-control")

        if not can_official:
            if self.instance and self.instance.pk and self.instance.tier == Competition.Tier.OFFICIAL:
                self.fields["tier"].disabled = True
                self.fields["tier"].initial = self.instance.tier
            else:
                self.fields["tier"].widget = forms.HiddenInput()
                self.fields["tier"].initial = Competition.Tier.UNOFFICIAL

        rules = normalize_rules(getattr(self.instance, "scoring_rules", None))
        mode = rules["mode"]
        params = rules["params"]
        tie = (rules.get("tie_breaker") or {}).get("preset")

        self.fields["scoring_mode"].initial = mode
        self.fields["tie_breaker_preset"].initial = tie

        self.fields["count_points_per_catch"].initial = int(params.get("points_per_catch", 10))
        self.fields["length_points_per_cm"].initial = Decimal(str(params.get("points_per_cm", "1")))
        self.fields["weight_points_per_kg"].initial = Decimal(str(params.get("points_per_kg", "10")))

        species_points = params.get("species_points") or {}
        if species_points:
            lines = []
            for key, value in species_points.items():
                lines.append(f"{key}={value}")
            self.fields["species_points_text"].initial = "\n".join(lines)

        self.fields["species_default_points"].initial = int(params.get("default_species_points", 0))
        self.fields["combo_selected_modes"].initial = list(params.get("selected_modes") or [])

        self.species_catalog = list(FISH_SPECIES)

    def clean(self):
        # Validuje základné dáta súťaže a scoring polia podľa zvoleného režimu.
        cleaned = super().clean()

        starts_at = cleaned.get("starts_at")
        ends_at = cleaned.get("ends_at")
        if starts_at and ends_at and ends_at <= starts_at:
            self.add_error("ends_at", "Koniec musí byť po začiatku.")

        tier = cleaned.get("tier")
        can_official = user_is_premium(self.user)

        if (
            tier == Competition.Tier.OFFICIAL
            and not can_official
            and not (self.instance and self.instance.tier == Competition.Tier.OFFICIAL)
        ):
            self.add_error("tier", "Nemáš oprávnenie vytvoriť oficiálnu súťaž.")

        mode = cleaned.get("scoring_mode") or ScoringMode.COUNT

        if mode == ScoringMode.COUNT:
            if cleaned.get("count_points_per_catch") is None:
                self.add_error("count_points_per_catch", "Zadaj body za úlovok.")

        elif mode in (ScoringMode.SUM_LENGTH, ScoringMode.BEST_LENGTH):
            if cleaned.get("length_points_per_cm") is None:
                self.add_error("length_points_per_cm", "Zadaj body za 1 cm.")

        elif mode in (ScoringMode.SUM_WEIGHT, ScoringMode.BEST_WEIGHT):
            if cleaned.get("weight_points_per_kg") is None:
                self.add_error("weight_points_per_kg", "Zadaj body za 1 kg.")

        elif mode == ScoringMode.SPECIES_TABLE:
            if cleaned.get("species_default_points") is None:
                self.add_error("species_default_points", "Zadaj default body (môže byť 0).")

        elif mode == ScoringMode.COMBO:
            combo_selected_modes = set(cleaned.get("combo_selected_modes") or [])

            if len(combo_selected_modes) < 2:
                self.add_error("combo_selected_modes", "Vyber aspoň 2 bodovacie systémy.")

            if ScoringMode.COUNT in combo_selected_modes and cleaned.get("count_points_per_catch") is None:
                self.add_error("count_points_per_catch", "Zadaj body za úlovok.")

            if (
                ScoringMode.SUM_LENGTH in combo_selected_modes
                or ScoringMode.BEST_LENGTH in combo_selected_modes
            ) and cleaned.get("length_points_per_cm") is None:
                self.add_error("length_points_per_cm", "Zadaj body za 1 cm.")

            if (
                ScoringMode.SUM_WEIGHT in combo_selected_modes
                or ScoringMode.BEST_WEIGHT in combo_selected_modes
            ) and cleaned.get("weight_points_per_kg") is None:
                self.add_error("weight_points_per_kg", "Zadaj body za 1 kg.")

            if ScoringMode.SPECIES_TABLE in combo_selected_modes and cleaned.get("species_default_points") is None:
                self.add_error("species_default_points", "Zadaj default body (môže byť 0).")

        return cleaned

    def save(self, commit=True):
        # Uloží scoring pravidlá do JSON poľa competition.scoring_rules.
        instance: Competition = super().save(commit=False)

        mode = self.cleaned_data.get("scoring_mode") or ScoringMode.COUNT
        tie = self.cleaned_data.get("tie_breaker_preset") or TieBreakerPreset.AUTO

        params: dict = {}
        requirements = {"length_required": False, "weight_required": False}

        if mode == ScoringMode.COUNT:
            params["points_per_catch"] = int(self.cleaned_data.get("count_points_per_catch") or 0)

        elif mode in (ScoringMode.SUM_LENGTH, ScoringMode.BEST_LENGTH):
            params["points_per_cm"] = str(self.cleaned_data.get("length_points_per_cm") or Decimal("0"))
            requirements["length_required"] = True

        elif mode in (ScoringMode.SUM_WEIGHT, ScoringMode.BEST_WEIGHT):
            params["points_per_kg"] = str(self.cleaned_data.get("weight_points_per_kg") or Decimal("0"))
            requirements["weight_required"] = True

        elif mode == ScoringMode.SPECIES_TABLE:
            params["species_points"] = parse_species_points(self.cleaned_data.get("species_points_text") or "")
            params["default_species_points"] = int(self.cleaned_data.get("species_default_points") or 0)

        elif mode == ScoringMode.COMBO:
            combo_selected_modes = list(self.cleaned_data.get("combo_selected_modes") or [])
            params["selected_modes"] = combo_selected_modes

            if ScoringMode.COUNT in combo_selected_modes:
                params["points_per_catch"] = int(self.cleaned_data.get("count_points_per_catch") or 0)

            if (
                ScoringMode.SUM_LENGTH in combo_selected_modes
                or ScoringMode.BEST_LENGTH in combo_selected_modes
            ):
                params["points_per_cm"] = str(self.cleaned_data.get("length_points_per_cm") or Decimal("0"))

            if (
                ScoringMode.SUM_WEIGHT in combo_selected_modes
                or ScoringMode.BEST_WEIGHT in combo_selected_modes
            ):
                params["points_per_kg"] = str(self.cleaned_data.get("weight_points_per_kg") or Decimal("0"))

            if ScoringMode.SPECIES_TABLE in combo_selected_modes:
                params["species_points"] = parse_species_points(self.cleaned_data.get("species_points_text") or "")
                params["default_species_points"] = int(self.cleaned_data.get("species_default_points") or 0)

            requirements["length_required"] = (
                ScoringMode.SUM_LENGTH in combo_selected_modes
                or ScoringMode.BEST_LENGTH in combo_selected_modes
            )
            requirements["weight_required"] = (
                ScoringMode.SUM_WEIGHT in combo_selected_modes
                or ScoringMode.BEST_WEIGHT in combo_selected_modes
            )

        instance.scoring_rules = {
            "version": 1,
            "mode": mode,
            "params": params,
            "tie_breaker": {"preset": tie},
            "requirements": requirements,
        }

        if commit:
            instance.save()
            self.save_m2m()
        return instance