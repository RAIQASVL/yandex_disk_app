from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class PublicLink(models.Model):
    """Model for storing public Yandex.Disk links."""

    publick_key = models.CharField(
        _("Public Key"), max_length=255, help_text=("Yandex.Disk public link key")
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="public_links",
        help_text=_("User who added this link"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_accessed = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Public Link")
        verbose_name_plural = _("Public Links")
        ordering = ["-last_accessed"]

    def __str__(self):
        return f"{self.publick_key} ({self.user.username})"
