"""Navigation items for the Device Library plugin."""

from netbox.plugins import PluginMenuItem


menu_items = (
    PluginMenuItem(
        link="plugins:netbox_plugin_device_library:settings",
        link_text="Settings",
        permissions=["netbox_plugin_device_library.change_librarysource"],
    ),
)
