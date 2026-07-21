from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("netbox_plugin_device_library", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="DeviceType",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("manufacturer_name", models.CharField(max_length=100)),
                ("name", models.CharField(max_length=200)),
                ("part_number", models.CharField(blank=True, max_length=200)),
                (
                    "github_api_url",
                    models.URLField(
                        help_text="GitHub API URL for the YAML document from which this object was imported.",
                        max_length=500,
                    ),
                ),
            ],
            options={
                "ordering": ("manufacturer_name", "name"),
            },
        ),
        migrations.CreateModel(
            name="ModuleType",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("manufacturer_name", models.CharField(max_length=100)),
                ("name", models.CharField(max_length=200)),
                ("part_number", models.CharField(blank=True, max_length=200)),
                (
                    "github_api_url",
                    models.URLField(
                        help_text="GitHub API URL for the YAML document from which this object was imported.",
                        max_length=500,
                    ),
                ),
            ],
            options={
                "ordering": ("manufacturer_name", "name"),
            },
        ),
        migrations.CreateModel(
            name="RackType",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("manufacturer_name", models.CharField(max_length=100)),
                ("name", models.CharField(max_length=200)),
                ("part_number", models.CharField(blank=True, max_length=200)),
                (
                    "github_api_url",
                    models.URLField(
                        help_text="GitHub API URL for the YAML document from which this object was imported.",
                        max_length=500,
                    ),
                ),
            ],
            options={
                "ordering": ("manufacturer_name", "name"),
            },
        ),
        migrations.RunSQL(
            sql="""
                CREATE INDEX netbox_plugin_device_library_devicetype_fts_idx
                ON netbox_plugin_device_library_devicetype
                USING GIN (
                    to_tsvector(
                        'english',
                        coalesce(manufacturer_name, '') || ' ' ||
                        coalesce(name, '') || ' ' ||
                        coalesce(part_number, '')
                    )
                );

                CREATE INDEX netbox_plugin_device_library_moduletype_fts_idx
                ON netbox_plugin_device_library_moduletype
                USING GIN (
                    to_tsvector(
                        'english',
                        coalesce(manufacturer_name, '') || ' ' ||
                        coalesce(name, '') || ' ' ||
                        coalesce(part_number, '')
                    )
                );

                CREATE INDEX netbox_plugin_device_library_racktype_fts_idx
                ON netbox_plugin_device_library_racktype
                USING GIN (
                    to_tsvector(
                        'english',
                        coalesce(manufacturer_name, '') || ' ' ||
                        coalesce(name, '') || ' ' ||
                        coalesce(part_number, '')
                    )
                );
            """,
            reverse_sql="""
                DROP INDEX netbox_plugin_device_library_devicetype_fts_idx;
                DROP INDEX netbox_plugin_device_library_moduletype_fts_idx;
                DROP INDEX netbox_plugin_device_library_racktype_fts_idx;
            """,
        ),
    ]
