from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("competitions", "0005_rename_competitions_invitation_comp_kind_idx_competition_competi_f245b8_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="invitation",
            name="spot_number",
            field=models.PositiveSmallIntegerField(blank=True, db_index=True, null=True),
        ),
    ]
