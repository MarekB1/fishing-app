from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("competitions", "0009_competitionmembership_is_organizer"),
    ]

    operations = [
        migrations.AlterField(
            model_name="competitionmembership",
            name="is_organizer",
            field=models.BooleanField(default=False, db_index=True),
        ),
        migrations.AddIndex(
            model_name="competitionmembership",
            index=models.Index(
                fields=["competition", "is_organizer"],
                name="comp_membership_comp_org_idx",
            ),
        ),
    ]