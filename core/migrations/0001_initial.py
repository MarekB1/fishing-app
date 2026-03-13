from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DashboardFeedback",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("section", models.CharField(choices=[
                    ("competitions", "Súťaže"),
                    ("competition_create", "Nová súťaž"),
                    ("invitations", "Pozvánky"),
                    ("catch_create", "Pridať úlovok"),
                    ("pending_catches", "Čaká na schválenie"),
                    ("scoreboard", "Scoreboard"),
                    ("my_catches", "Moje úlovky"),
                ], max_length=32, verbose_name="Sekcia")),
                ("feedback_type", models.CharField(choices=[
                    ("bug", "Bug"),
                    ("improvement", "Zlepšenie"),
                ], max_length=16, verbose_name="Typ")),
                ("description", models.TextField(verbose_name="Popis")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Vytvorené")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Upravené")),
                ("reporter", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="dashboard_feedbacks",
                    to=settings.AUTH_USER_MODEL,
                    verbose_name="Tester",
                )),
            ],
            options={
                "verbose_name": "Poznámka z dashboardu",
                "verbose_name_plural": "Poznámky z dashboardu",
                "ordering": ("-created_at",),
            },
        ),
        migrations.AddIndex(
            model_name="dashboardfeedback",
            index=models.Index(fields=["created_at"], name="core_dashbo_created_2dca2f_idx"),
        ),
        migrations.AddIndex(
            model_name="dashboardfeedback",
            index=models.Index(fields=["section", "feedback_type"], name="core_dashbo_section_f5a0fc_idx"),
        ),
        migrations.AddIndex(
            model_name="dashboardfeedback",
            index=models.Index(fields=["reporter", "created_at"], name="core_dashbo_reporte_25f530_idx"),
        ),
    ]