# apps/competitions/migrations/0004_competition_tier.py
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("competitions", "0003_invitation_multiuse_link_and_uses"),
    ]

    operations = [
        migrations.AddField(
            model_name="competition",
            name="tier",
            field=models.CharField(
                choices=[("UNOFFICIAL", "Neoficiálna"), ("OFFICIAL", "Oficiálna")],
                db_index=True,
                default="UNOFFICIAL",
                max_length=12,
            ),
        ),
    ]
