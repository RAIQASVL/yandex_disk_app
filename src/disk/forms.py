from django import forms
from django.utils.translation import gettext_lazy as _


class PublicLinkForm(forms.Form):
    public_key = forms.CharField(
        label=_("Public Link"),
        max_length=255,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter Yandex.Disk public link",
            }
        ),
    )
    file_type = forms.ChoiceField(
        label=_("File Type"),
        required=False,
        choices=[
            ("", "All Files"),
            ("document", "Documents"),
            ("image", "Images"),
            ("video", "Videos"),
            ("audio", "Audio"),
        ],
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    def clean_public_key(self):
        """Extract public key from full URL if needed."""
        public_key = self.cleaned_data["public_key"]

        # Handle full URLs
        if "disk.yandex.ru" in public_key:
            # Extract the public key from the URL
            # Example: https://disk.yandex.ru/d/XXXXX -> XXXXX
            public_key = public_key.split("/")[-1]

        return public_key
