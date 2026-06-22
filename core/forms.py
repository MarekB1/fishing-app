from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordChangeForm

from .models import TodoTask
from .models import DashboardFeedback

User = get_user_model()


class BootstrapFormMixin:
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


class ProfileUpdateForm(BootstrapFormMixin, forms.ModelForm):
    avatar = forms.ImageField(required=False, label="Profilová fotka (nepovinné)")

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        labels = {
            'first_name': 'Krstné meno',
            'last_name': 'Priezvisko',
            'email': 'E-mailová adresa'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if self.instance and hasattr(self.instance, 'profile'):
            self.fields['avatar'].initial = self.instance.profile.avatar

        self._bootstrapify() 

    def save(self, commit=True):
        user = super().save(commit=commit)
        
        avatar = self.cleaned_data.get('avatar')
        
        if hasattr(user, 'profile'):
            if 'avatar' in self.changed_data:
                user.profile.avatar = avatar
                
            if commit:
                user.profile.save()
            
        return user


class BootstrapPasswordChangeForm(BootstrapFormMixin, PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if "old_password" in self.fields:
            self.fields["old_password"].label = "Aktuálne heslo"
            self.fields["old_password"].widget.attrs["autocomplete"] = "current-password"

        if "new_password1" in self.fields:
            self.fields["new_password1"].label = "Nové heslo"
            self.fields["new_password1"].widget.attrs["autocomplete"] = "new-password"

        if "new_password2" in self.fields:
            self.fields["new_password2"].label = "Nové heslo (znovu)"
            self.fields["new_password2"].widget.attrs["autocomplete"] = "new-password"

        self._bootstrapify()


class DashboardFeedbackForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = DashboardFeedback
        fields = ("section", "feedback_type", "description")
        labels = {
            "section": "Sekcia",
            "feedback_type": "Typ",
            "description": "Popis",
        }
        widgets = {
            "description": forms.Textarea(
                attrs={
                    "rows": 5,
                    "placeholder": "Popíš bug alebo návrh na zlepšenie...",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["section"].choices = [
            ("", "Vyber sekciu"),
            *DashboardFeedback.Section.choices,
        ]
        self.fields["feedback_type"].choices = [
            ("", "Vyber typ"),
            *DashboardFeedback.FeedbackType.choices,
        ]

        self._bootstrapify()

    def clean_description(self):
        value = (self.cleaned_data.get("description") or "").strip()
        if len(value) < 5:
            raise forms.ValidationError("Popis musí mať aspoň 5 znakov.")
        return value
    
class TodoTaskForm(forms.ModelForm):
    class Meta:
        model = TodoTask
        fields = ('title', 'description')
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Napr. Oprava schvaľovania fotiek'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3, 
                'placeholder': 'Podrobný popis, čo všetko treba spraviť...'
            }),
        }    