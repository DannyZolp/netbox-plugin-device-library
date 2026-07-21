"""Views for the Device Library plugin."""

from django.contrib import messages
from django.forms import modelformset_factory
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.generic import View
from utilities.views import ContentTypePermissionRequiredMixin

from .forms import LibrarySourceForm
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
        return render(request, self.template_name, {"formset": self.get_formset()})

    def post(self, request):
        formset = self.get_formset(request.POST)
        if formset.is_valid():
            formset.save()
            messages.success(request, "Device library settings saved.")
            return redirect(reverse("plugins:netbox_plugin_device_library:settings"))

        return render(request, self.template_name, {"formset": formset})
