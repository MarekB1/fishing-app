from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ("competitions", "0002_competition_location_spots_allow_photos"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="invitation",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="competition_invites_created",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="invitation",
            name="kind",
            field=models.CharField(
                choices=[("DIRECT", "Direct (single-use)"), ("LINK", "Share link (multi-use)")],
                db_index=True,
                default="DIRECT",
                max_length=12,
            ),
        ),
        migrations.AddField(
            model_name="invitation",
            name="max_uses",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="invitation",
            name="uses_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.CreateModel(
            name="InvitationUse",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("invitation", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="uses", to="competitions.invitation")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="competition_invite_uses", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddConstraint(
            model_name="invitationuse",
            constraint=models.UniqueConstraint(fields=("invitation", "user"), name="uniq_invitation_use_invitation_user"),
        ),
        migrations.AddIndex(
            model_name="invitationuse",
            index=models.Index(fields=["invitation", "created_at"], name="competitions_invitation_inv_created_6d0a92_idx"),
        ),
        migrations.AddIndex(
            model_name="invitationuse",
            index=models.Index(fields=["user", "created_at"], name="competitions_invitation_use_user_created_5f5a6c_idx"),
        ),
        migrations.AddConstraint(
            model_name="invitation",
            constraint=models.UniqueConstraint(fields=("competition",), condition=Q(kind="LINK"), name="uniq_competition_share_link"),
        ),
        migrations.AddIndex(
            model_name="invitation",
            index=models.Index(fields=["competition", "kind"], name="competitions_invitation_comp_kind_idx"),
        ),
    ]
