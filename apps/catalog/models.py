from django.conf import settings
from django.db import models
import uuid


def generate_passport_code():
    return f"AURA-{uuid.uuid4().hex[:16].upper()}"

class Product(models.Model):
    class PurchaseChannel(models.TextChoices):
        ONLINE = "ONLINE", "온라인"
        OFFLINE = "OFFLINE", "오프라인"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=120)
    brand = models.CharField(max_length=80, blank=True)
    category = models.CharField(max_length=50)
    purchased_at = models.DateField(null=True, blank=True)
    purchase_place = models.CharField(max_length=120, blank=True)
    purchase_channel = models.CharField(
        max_length=10, choices=PurchaseChannel.choices, blank=True
    )
    purchase_price = models.PositiveIntegerField(null=True, blank=True)
    memo = models.TextField(blank=True)
    image = models.ImageField(upload_to="products/", null=True, blank=True)
    passport_code = models.CharField(max_length=64, unique=True, default=generate_passport_code, editable=False)
    metadata = models.JSONField(default=dict, blank=True) # 색상, 소재, 보증 등
    created_at = models.DateTimeField(auto_now_add=True)

class ProductImage(models.Model):
    class Kind(models.TextChoices):
        PRODUCT = "PRODUCT", "제품"
        RECEIPT = "RECEIPT", "영수증"
        WARRANTY = "WARRANTY", "보증서"

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/")
    is_receipt = models.BooleanField(default=False)
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.PRODUCT)
    created_at = models.DateTimeField(auto_now_add=True)

class CareBookmark(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    guide_id = models.PositiveIntegerField()  # care.CareGuide id; app dependency is kept one-way
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("user", "guide_id"), name="unique_care_bookmark")]
