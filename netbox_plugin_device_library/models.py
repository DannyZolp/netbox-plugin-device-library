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


class ImportedLibraryObject(models.Model):
    """Common source metadata for an imported device-library object."""

    manufacturer_name = models.CharField(max_length=100)
    name = models.CharField(max_length=200)
    part_number = models.CharField(max_length=200, blank=True)
    github_api_url = models.URLField(
        max_length=500,
        unique=True,
        help_text="GitHub API URL for the YAML document from which this object was imported.",
    )

    class Meta:
        abstract = True
        ordering = ("manufacturer_name", "name")

    def __str__(self):
        return f"{self.manufacturer_name} {self.name}"


class DeviceType(ImportedLibraryObject):
    """A device type imported from a device-library YAML document."""


class ModuleType(ImportedLibraryObject):
    """A module type imported from a device-library YAML document."""


class RackType(ImportedLibraryObject):
    """A rack type imported from a device-library YAML document."""


class Image(models.Model):
    """An image referenced by a device-library object."""

    slug = models.SlugField(max_length=100)
    face = models.CharField(max_length=10)
    uri = models.URLField(max_length=500)

    class Meta:
        db_table = "netbox_plugin_device_library_images"
        ordering = ("slug", "face")

    def __str__(self):
        return f"{self.slug} ({self.face})"
