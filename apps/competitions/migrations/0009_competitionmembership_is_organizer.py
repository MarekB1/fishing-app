from django.db import migrations, models
from django.db.models import F


def forwards(apps, schema_editor):
    CompetitionMembership = apps.get_model("competitions", "CompetitionMembership")

    # pôvodní organizátori -> contestant + organizer privilege
    CompetitionMembership.objects.filter(
        role="ORGANIZER"
    ).update(
        role="CONTESTANT",
        is_organizer=True,
    )

    # creator súťaže nech je vždy organizer
    CompetitionMembership.objects.filter(
        competition__created_by_id=F("user_id")
    ).update(
        is_organizer=True,
    )


def backwards(apps, schema_editor):
    # noop
    pass


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("competitions", "0008_premium_permission"),
    ]

    operations = [
        migrations.AddField(
            model_name="competitionmembership",
            name="is_organizer",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(forwards, backwards),
    ]