__author__ = "Danny Zolp"
__email__ = "danny@zolp.io"
__version__ = "0.1.0"


from netbox.plugins import PluginConfig


class DeviceLibraryConfig(PluginConfig):
    name = "netbox_plugin_device_library"
    verbose_name = "Device Library"
    description = "A simple plugin that integrates the Netbox device library with your instance to allow for simple importing."
    author = "Danny Zolp"
    author_email = "danny@zolp.io"
    version = __version__
    base_url = "device-library"
    min_version = "4.5.0"
    max_version = "4.5.99"


config = DeviceLibraryConfig
