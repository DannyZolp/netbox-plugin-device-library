from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("netbox_plugin_device_library", "0003_unique_import_urls"),
    ]

    operations = [
        migrations.CreateModel(
            name="Image",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(max_length=100)),
                ("face", models.CharField(max_length=10)),
                ("uri", models.URLField(max_length=500)),
            ],
            options={
                "db_table": "netbox_plugin_device_library_images",
                "ordering": ("slug", "face"),
            },
        ),
    ]
