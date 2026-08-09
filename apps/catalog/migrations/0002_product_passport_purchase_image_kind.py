import apps.catalog.models
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("catalog", "0001_initial")]

    operations = [
        migrations.AddField(model_name="product", name="purchase_place", field=models.CharField(blank=True, max_length=120)),
        migrations.AddField(model_name="product", name="purchase_channel", field=models.CharField(blank=True, max_length=30)),
        migrations.AddField(model_name="product", name="memo", field=models.TextField(blank=True)),
        migrations.AlterField(model_name="product", name="passport_code", field=models.CharField(default=apps.catalog.models.generate_passport_code, editable=False, max_length=64, unique=True)),
        migrations.AddField(model_name="productimage", name="kind", field=models.CharField(choices=[("PRODUCT", "제품"), ("RECEIPT", "영수증"), ("WARRANTY", "보증서")], default="PRODUCT", max_length=10)),
    ]
