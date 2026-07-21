"""Template extensions for core NetBox object list views."""

from netbox.plugins import PluginTemplateExtension


class AddFromLibraryButton(PluginTemplateExtension):
    """Add a link to the library search for one imported object type."""

    object_type = None

    def list_buttons(self):
        return self.render(
            "netbox_plugin_device_library/partials/add_from_library_button.html",
            extra_context={"object_type": self.object_type},
        )


class DeviceTypeAddFromLibraryButton(AddFromLibraryButton):
    models = ["dcim.devicetype"]
    object_type = "device"


class ModuleTypeAddFromLibraryButton(AddFromLibraryButton):
    models = ["dcim.moduletype"]
    object_type = "module"


class RackTypeAddFromLibraryButton(AddFromLibraryButton):
    models = ["dcim.racktype"]
    object_type = "rack"


template_extensions = [
    DeviceTypeAddFromLibraryButton,
    ModuleTypeAddFromLibraryButton,
    RackTypeAddFromLibraryButton,
]
