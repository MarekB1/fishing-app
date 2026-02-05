from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ("competitions", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="competition",
            name="location_name",
            field=models.CharField(default="", max_length=255),
        ),
        migrations.AddField(
            model_name="competition",
            name="fishing_spots_count",
            field=models.PositiveSmallIntegerField(
                default=1,
                validators=[django.core.validators.MinValueValidator(1)],
            ),
        ),
        migrations.AddField(
            model_name="competition",
            name="allow_photos",
            field=models.BooleanField(default=True),
        ),
    ]
