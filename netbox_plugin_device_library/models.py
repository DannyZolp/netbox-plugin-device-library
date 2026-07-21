"""Database models for the Device Library plugin."""

from django.db import models


class LibrarySource(models.Model):
    """A Git repository containing NetBox device-library definitions."""

    repository = models.URLField(
        max_length=500,
        unique=True,
        help_text="The HTTPS URL of a device-library Git repository.",
    )

    class Meta:
        ordering = ("repository",)
        verbose_name = "library source"
        verbose_name_plural = "library sources"

    def __str__(self):
        return self.repository
