from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="LibrarySource",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "repository",
                    models.URLField(
                        help_text="The HTTPS URL of a device-library GitHub repository.",
                        max_length=500,
                        unique=True,
                    ),
                ),
            ],
            options={
                "ordering": ("repository",),
                "verbose_name": "library source",
                "verbose_name_plural": "library sources",
            },
        ),
    ]
