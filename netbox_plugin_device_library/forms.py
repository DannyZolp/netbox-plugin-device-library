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
                }
            )
        }
