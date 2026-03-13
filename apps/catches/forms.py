from io import BytesIO
from pathlib import Path

from attrs import field
from .constants import FISH_SPECIES_CHOICES
from django import forms
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image, ImageOps, UnidentifiedImageError

from .models import Catch

DT_LOCAL_FORMAT = "%Y-%m-%dT%H:%M"
RAW_PHOTO_MAX_MB = 25
NORMALIZED_PHOTO_MAX_MB = 8
MAX_PHOTO_SIDE_PX = 2560
ALLOWED_PHOTO_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
}
ALLOWED_PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
HEIF_CONTENT_TYPES = {"image/heic", "image/heif"}
HEIF_EXTENSIONS = {".heic", ".heif"}

try:
    import pillow_heif  # noqa: F401
    HEIF_SUPPORT_ENABLED = True
except ImportError:
    HEIF_SUPPORT_ENABLED = False


def _get_uploaded_photo_extension(photo) -> str:
    """Vráti príponu uploadnutého súboru v lowercase tvare."""
    return Path(getattr(photo, "name", "") or "").suffix.lower()


def _get_uploaded_photo_content_type(photo) -> str:
    """Vráti MIME typ uploadnutého súboru v lowercase tvare."""
    return (getattr(photo, "content_type", "") or "").lower()


def _is_allowed_photo_type(photo) -> bool:
    """Overí, či upload patrí medzi podporované formáty podľa MIME typu alebo prípony."""
    extension = _get_uploaded_photo_extension(photo)
    content_type = _get_uploaded_photo_content_type(photo)
    return extension in ALLOWED_PHOTO_EXTENSIONS or content_type in ALLOWED_PHOTO_CONTENT_TYPES


def _is_heif_photo(photo) -> bool:
    """Zistí, či ide o HEIC/HEIF fotku typickú najmä pre iPhone."""
    extension = _get_uploaded_photo_extension(photo)
    content_type = _get_uploaded_photo_content_type(photo)
    return extension in HEIF_EXTENSIONS or content_type in HEIF_CONTENT_TYPES


def _normalize_uploaded_photo_to_jpeg(photo) -> SimpleUploadedFile:
    """Prevedie uploadnutý obrázok na otočený a zmenšený JPEG vhodný na uloženie aj zobrazenie."""
    photo.seek(0)

    with Image.open(photo) as image:
        image = ImageOps.exif_transpose(image)

        if image.mode not in ("RGB", "L"):
            alpha_image = image.convert("RGBA")
            background = Image.new("RGB", alpha_image.size, (255, 255, 255))
            background.paste(alpha_image, mask=alpha_image.getchannel("A"))
            image = background
        else:
            image = image.convert("RGB")

        if max(image.size) > MAX_PHOTO_SIDE_PX:
            image.thumbnail((MAX_PHOTO_SIDE_PX, MAX_PHOTO_SIDE_PX), Image.Resampling.LANCZOS)

        output = BytesIO()
        image.save(output, format="JPEG", quality=85, optimize=True)

    output.seek(0)
    file_stem = Path(getattr(photo, "name", "catch-photo") or "catch-photo").stem or "catch-photo"
    normalized_name = f"{file_stem}.jpg"

    return SimpleUploadedFile(
        normalized_name,
        output.read(),
        content_type="image/jpeg",
    )

FISH_SPECIES_CHOICES = [
    ("", "Vyber druh ryby"),
    ("Kapor", "Kapor"),
    ("Amur", "Amur"),
    ("Šťuka", "Šťuka"),
    ("Zubáč", "Zubáč"),
    ("Sumec", "Sumec"),
    ("Ostriež", "Ostriež"),
    ("Pstruh", "Pstruh"),
    ("Lipeň", "Lipeň"),
    ("Jelec", "Jelec"),
    ("Plotica", "Plotica"),
    ("Pleskáč", "Pleskáč"),
    ("Tolstolobik", "Tolstolobik"),
    ("Karas", "Karas"),
    ("Lín", "Lín"),
    ("Úhor", "Úhor"),
]

class CatchCreateForm(forms.ModelForm):
    photo = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(
            attrs={
                "accept": "image/jpeg,image/png,image/webp,image/heic,image/heif,.jpg,.jpeg,.png,.webp,.heic,.heif",
            }
        ),
    )

    class Meta:
        model = Catch
        fields = ["competition", "species", "length_cm", "weight_kg", "caught_at", "note", "photo"]
        widgets = {
            "competition": forms.Select(),
            "species": forms.Select(choices=FISH_SPECIES_CHOICES),
            "caught_at": forms.DateTimeInput(format=DT_LOCAL_FORMAT, attrs={"type": "datetime-local"}),
            "note": forms.Textarea(attrs={"rows": 3}),
            "length_cm": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "weight_kg": forms.NumberInput(attrs={"step": "0.001", "min": "0"}),
        }

    def __init__(self, *args, competition_qs=None, **kwargs):
        """Nastaví povolené súťaže a základné CSS triedy pre formulár."""
        super().__init__(*args, **kwargs)

        if competition_qs is not None:
            self.fields["competition"].queryset = competition_qs

        for field_name, field in self.fields.items():
            existing_class = field.widget.attrs.get("class", "")
            if field_name == "photo":
                field.widget.attrs["class"] = f"{existing_class} form-control".strip()
            elif field_name in {"competition", "species"}:
                field.widget.attrs["class"] = f"{existing_class} form-select".strip()
            else:
                field.widget.attrs["class"] = f"{existing_class} form-control".strip()

    def clean_photo(self):
        """Validuje upload a všetky podporované formáty zjednotí na JPEG."""
        photo = self.cleaned_data.get("photo")
        if not photo:
            return photo

        if photo.size > RAW_PHOTO_MAX_MB * 1024 * 1024:
            raise forms.ValidationError(f"Pôvodná fotka je príliš veľká (max {RAW_PHOTO_MAX_MB}MB).")

        if not _is_allowed_photo_type(photo):
            raise forms.ValidationError("Povolené sú iba JPG, PNG, WEBP, HEIC alebo HEIF.")

        if _is_heif_photo(photo) and not HEIF_SUPPORT_ENABLED:
            raise forms.ValidationError(
                "Server zatiaľ nepodporuje HEIC/HEIF. Doinštaluj pillow-heif."
            )

        try:
            normalized_photo = _normalize_uploaded_photo_to_jpeg(photo)
        except UnidentifiedImageError as exc:
            raise forms.ValidationError("Nepodarilo sa načítať obrázok. Skús inú fotku alebo ju ulož znova.") from exc
        except OSError as exc:
            raise forms.ValidationError("Fotku sa nepodarilo spracovať. Skús ju vyexportovať znova ako obrázok.") from exc

        if normalized_photo.size > NORMALIZED_PHOTO_MAX_MB * 1024 * 1024:
            raise forms.ValidationError(
                f"Spracovaná fotka je stále príliš veľká (max {NORMALIZED_PHOTO_MAX_MB}MB)."
            )

        return normalized_photo

    def clean(self):
        """Skontroluje pravidlá súťaže a základnú logiku polí formulára."""
        cleaned = super().clean()
        competition = cleaned.get("competition")
        caught_at = cleaned.get("caught_at")
        photo = cleaned.get("photo")

        length_cm = cleaned.get("length_cm")
        weight_kg = cleaned.get("weight_kg")

        if competition and not getattr(competition, "allow_photos", True) and photo:
            self.add_error("photo", "Táto súťaž nepovoľuje pridávanie fotiek.")

        if competition:
            rules = getattr(competition, "scoring_rules", {}) or {}
            req = rules.get("requirements", {}) or {}
            if req.get("length_required") and not length_cm:
                self.add_error("length_cm", "Pre toto bodovanie je dĺžka povinná.")
            if req.get("weight_required") and not weight_kg:
                self.add_error("weight_kg", "Pre toto bodovanie je váha povinná.")

        if length_cm is not None and length_cm <= 0:
            self.add_error("length_cm", "Dĺžka musí byť väčšia ako 0.")
        if weight_kg is not None and weight_kg <= 0:
            self.add_error("weight_kg", "Váha musí byť väčšia ako 0.")

        if competition and caught_at:
            if not (competition.starts_at <= caught_at <= competition.ends_at):
                self.add_error("caught_at", "Čas úlovku musí byť v rámci trvania súťaže.")

        return cleaned