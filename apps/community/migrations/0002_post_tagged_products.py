from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("catalog", "0002_product_passport_purchase_image_kind"), ("community", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="post",
            name="tagged_products",
            field=models.ManyToManyField(blank=True, related_name="community_posts", to="catalog.product"),
        ),
    ]
