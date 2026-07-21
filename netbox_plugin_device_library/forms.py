"""Forms for the Device Library plugin."""

from django import forms

from .models import LibrarySource


class LibrarySourceForm(forms.ModelForm):
    class Meta:
        model = LibrarySource
        fields = ("repository",)
        widgets = {
            "repository": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "https://github.com/user/netbox-device-library",
                    "pattern": r"https://github\.com/[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9._-]+(?:\.git)?/?",
                    "title": "Enter a HTTPS GitHub repository URL",
                }
            )
        }
