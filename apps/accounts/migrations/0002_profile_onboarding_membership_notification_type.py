from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0001_initial")]

    operations = [
        migrations.AddField(model_name="profile", name="gender", field=models.CharField(blank=True, choices=[("FEMALE", "여성"), ("MALE", "남성"), ("OTHER", "기타/응답 안 함")], max_length=10)),
        migrations.AddField(model_name="profile", name="age_range", field=models.CharField(blank=True, max_length=20)),
        migrations.AddField(model_name="profile", name="lifestyle", field=models.JSONField(blank=True, default=list)),
        migrations.AddField(model_name="profile", name="preferred_brands", field=models.JSONField(blank=True, default=list)),
        migrations.AddField(model_name="profile", name="min_budget", field=models.PositiveIntegerField(blank=True, null=True)),
        migrations.AddField(model_name="profile", name="max_budget", field=models.PositiveIntegerField(blank=True, null=True)),
        migrations.AddField(model_name="profile", name="membership_tier", field=models.CharField(default="AURA Silver", max_length=30)),
        migrations.AddField(model_name="profile", name="membership_points", field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name="notification", name="type", field=models.CharField(choices=[("CARE", "케어 알림"), ("MEMBERSHIP", "멤버십"), ("EVENT", "이벤트"), ("GENERAL", "일반")], default="GENERAL", max_length=15)),
        migrations.AddField(model_name="notification", name="action_url", field=models.CharField(blank=True, max_length=255)),
    ]
