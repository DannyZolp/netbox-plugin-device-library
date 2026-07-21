"""Views for the Device Library plugin."""

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.forms import modelformset_factory
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.generic import View
from core.choices import JobStatusChoices
from utilities.views import ContentTypePermissionRequiredMixin

from .forms import LibrarySourceForm
from .jobs import DeviceLibrarySyncJob
from .models import LibrarySource
from .models import DeviceType, ModuleType, RackType


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
        library_search_type = request.GET.get("library_type", "device")
        if library_search_type not in LibrarySearchView.models_by_type:
            library_search_type = "device"

        return render(
            request,
            self.template_name,
            {
                "formset": self.get_formset(),
                "sync_running": sync_job_is_enqueued(),
                "library_search_type": library_search_type,
                "open_library_search": "library_type" in request.GET,
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
                "library_search_type": "device",
                "open_library_search": False,
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


class LibrarySearchView(ContentTypePermissionRequiredMixin, View):
    """Return a paginated, searchable list of imported library objects."""

    template_name = "netbox_plugin_device_library/partials/library_search_results.html"
    page_size = 25
    models_by_type = {
        "device": DeviceType,
        "module": ModuleType,
        "rack": RackType,
    }

    def get_required_permission(self):
        return "netbox_plugin_device_library.change_librarysource"

    def get(self, request):
        object_type = request.GET.get("object_type", "device")
        model = self.models_by_type.get(object_type, DeviceType)
        if object_type not in self.models_by_type:
            object_type = "device"

        query = request.GET.get("q", "").strip()
        queryset = model.objects.order_by("manufacturer_name", "name")
        if query:
            queryset = queryset.filter(
                Q(manufacturer_name__icontains=query)
                | Q(name__icontains=query)
                | Q(part_number__icontains=query)
            )

        page_obj = Paginator(queryset, self.page_size).get_page(request.GET.get("page"))
        return render(
            request,
            self.template_name,
            {
                "object_type": object_type,
                "page_obj": page_obj,
                "query": query,
            },
        )
