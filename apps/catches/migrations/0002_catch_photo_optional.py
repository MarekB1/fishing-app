from django.db import migrations, models
import apps.catches.models


class Migration(migrations.Migration):

    dependencies = [
        ("catches", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="catch",
            name="photo",
            field=models.ImageField(
                upload_to=apps.catches.models.catch_photo_upload_to,
                blank=True,
                null=True,
            ),
        ),
    ]
