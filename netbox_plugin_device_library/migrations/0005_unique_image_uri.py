from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("netbox_plugin_device_library", "0004_images"),
    ]

    operations = [
        migrations.AlterField(
            model_name="image",
            name="uri",
            field=models.URLField(max_length=500, unique=True),
        ),
    ]
