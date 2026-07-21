from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("netbox_plugin_device_library", "0002_imported_library_objects"),
    ]

    operations = [
        migrations.AlterField(
            model_name="devicetype",
            name="github_api_url",
            field=models.URLField(
                help_text="GitHub API URL for the YAML document from which this object was imported.",
                max_length=500,
                unique=True,
            ),
        ),
        migrations.AlterField(
            model_name="moduletype",
            name="github_api_url",
            field=models.URLField(
                help_text="GitHub API URL for the YAML document from which this object was imported.",
                max_length=500,
                unique=True,
            ),
        ),
        migrations.AlterField(
            model_name="racktype",
            name="github_api_url",
            field=models.URLField(
                help_text="GitHub API URL for the YAML document from which this object was imported.",
                max_length=500,
                unique=True,
            ),
        ),
    ]
