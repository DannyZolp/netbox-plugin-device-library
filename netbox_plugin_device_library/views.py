"""Views for the Device Library plugin."""

from django.contrib import messages
from django.db import transaction
from django.forms import modelformset_factory
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.generic import View
from core.choices import JobStatusChoices
from utilities.views import ContentTypePermissionRequiredMixin

from .forms import LibrarySourceForm
from .jobs import DeviceLibrarySyncJob
from .models import LibrarySource


class SettingsView(ContentTypePermissionRequiredMixin, View):
    """Manage the device-library repositories available to this plugin."""

    template_name = "netbox_plugin_device_library/settings.html"

    def get_required_permission(self):
        return "netbox_plugin_device_library.change_librarysource"

    @staticmethod
    def get_formset(*args, **kwargs):
        formset_class = modelformset_factory(
            LibrarySource,
            form=LibrarySourceForm,
            extra=0,
            can_delete=True,
        )
        return formset_class(*args, queryset=LibrarySource.objects.all(), **kwargs)

    def get(self, request):
        return render(
            request,
            self.template_name,
            {
                "formset": self.get_formset(),
                "sync_running": sync_job_is_enqueued(),
            },
        )

    def post(self, request):
        formset = self.get_formset(request.POST)
        if formset.is_valid():
            with transaction.atomic():
                formset.save()
            messages.success(request, "Device library settings saved.")
            return redirect(reverse("plugins:netbox_plugin_device_library:settings"))

        return render(
            request,
            self.template_name,
            {
                "formset": formset,
                "sync_running": sync_job_is_enqueued(),
            },
        )


class SyncAllLibrariesView(ContentTypePermissionRequiredMixin, View):
    """Queue a synchronization job for every configured library source."""

    http_method_names = ["post"]

    def get_required_permission(self):
        return "netbox_plugin_device_library.change_librarysource"

    def post(self, request):
        if sync_job_is_enqueued():
            messages.warning(request, "A device library synchronization is already in progress.")
            return redirect(reverse("plugins:netbox_plugin_device_library:settings"))

        DeviceLibrarySyncJob.enqueue_once(user=request.user)
        messages.success(request, "Device library synchronization queued.")
        return redirect(reverse("plugins:netbox_plugin_device_library:settings"))


def sync_job_is_enqueued():
    """Return whether a device-library sync is pending, scheduled, or running."""
    return DeviceLibrarySyncJob.get_jobs().filter(
        status__in=JobStatusChoices.ENQUEUED_STATE_CHOICES
    ).exists()
