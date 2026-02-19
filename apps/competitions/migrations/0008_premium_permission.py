from django.db import migrations


def forwards(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    User = apps.get_model("auth", "User")
    Group = apps.get_model("auth", "Group")

    # ContentType pre competitions.Competition
    ct, _ = ContentType.objects.get_or_create(app_label="competitions", model="competition")

    # Nový premium perm
    premium_perm, _ = Permission.objects.get_or_create(
        content_type=ct,
        codename="premium",
        defaults={"name": "Premium"},
    )
    # ak už existoval, upraceme názov
    if premium_perm.name != "Premium":
        premium_perm.name = "Premium"
        premium_perm.save(update_fields=["name"])

    # Legacy perm (ak si ho mal v DB)
    legacy = Permission.objects.filter(content_type=ct, codename="can_create_official_competitions").first()
    if not legacy:
        return

    # Prenes user perms
    for u in User.objects.filter(user_permissions=legacy).iterator():
        u.user_permissions.add(premium_perm)

    # Prenes group perms
    for g in Group.objects.filter(permissions=legacy).iterator():
        g.permissions.add(premium_perm)

    # Odstráň legacy perm (aby bol admin prehľadný)
    legacy.delete()


def backwards(apps, schema_editor):
    # nechávame noop – spätné vytváranie legacy perm netreba
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("competitions", "0007_competition_cancelled_at_and_more"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
