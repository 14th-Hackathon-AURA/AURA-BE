from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("accounts", "0002_profile_onboarding_membership_notification_type")]

    operations = [
        migrations.RemoveField(model_name="profile", name="membership_points"),
        migrations.RemoveField(model_name="profile", name="membership_tier"),
    ]
