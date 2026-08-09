from django.conf import settings
from django.db import models

class Product(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=120)
    brand = models.CharField(max_length=80, blank=True)
    category = models.CharField(max_length=50)
    purchased_at = models.DateField(null=True, blank=True)
    image = models.ImageField(upload_to="products/", null=True, blank=True)
    passport_code = models.CharField(max_length=64, unique=True)
    metadata = models.JSONField(default=dict, blank=True) # 색상, 소재, 보증 등
    created_at = models.DateTimeField(auto_now_add=True)

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/")
    is_receipt = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class CareBookmark(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    guide_id = models.PositiveIntegerField()  # care.CareGuide id; app dependency is kept one-way
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("user", "guide_id"), name="unique_care_bookmark")]
