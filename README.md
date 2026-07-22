# netbox-plugin-device-library
a plugin that allows you to add from the device library without downloading a gigabyte of YAML

---

## How to Setup

1. Install the plugin
2. Go to Plugins > Device Library > Settings
3. Copy a GitHub link to a device library you want to index
4. Press "Add Library", enter in your URL, and press save
5. Finally, press "Sync All Libraries" to index the GitHub repos you specified

## How to Use

Once you've installed, setup, and synced the plugin, you will see a new "Add from Library" button on the Device Type, Module Type, and Rack Type pages. Clicking this opens a modal where you can search for and add object types.

## Database Usage

After syncing the standard device library (https://github.com/netbox-community/devicetype-library), PostgreSQL increased by about 30 megabytes. While this is significiant, it's far less than importing every single device using the standard Device Type Library Import script and this setup requires no REST API calls (which Netbox Cloud charges for), and is significantly faster than said script. It will stream a tarball of the repo while indexing, so keep in mind that it will still use a decent portion of bandwidth.