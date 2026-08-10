from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("care", "0001_initial")]

    operations = [
        migrations.AddField(model_name="diagnosis", name="condition_level", field=models.CharField(blank=True, choices=[("SAFE", "양호"), ("CAUTION", "관리 필요"), ("DANGER", "점검 권장")], max_length=10)),
        migrations.AddField(model_name="diagnosis", name="damage_type", field=models.CharField(blank=True, max_length=80)),
        migrations.AddField(model_name="diagnosis", name="damage_description", field=models.TextField(blank=True)),
        migrations.AddField(model_name="diagnosis", name="care_suggestion", field=models.TextField(blank=True)),
        migrations.AddField(model_name="diagnosis", name="damage_location", field=models.JSONField(blank=True, default=dict)),
        migrations.AddField(model_name="careguide", name="source_name", field=models.CharField(blank=True, max_length=120)),
        migrations.AddField(model_name="careguide", name="source_url", field=models.URLField(blank=True)),
        migrations.AddField(model_name="careguide", name="season", field=models.CharField(blank=True, max_length=30)),
    ]
