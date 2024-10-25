from django import forms
from django.utils.translation import gettext_lazy as _


class PublicLinkForm(forms.Form):
    public_url = forms.URLField(
        label=_("Public URL"),
        widget=forms.URLInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter Yandex.Disk public URL",
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
