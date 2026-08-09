from rest_framework import serializers
from .models import CareBookmark, Product, ProductImage
class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ("id", "image", "is_receipt", "created_at")
        read_only_fields = ("id", "created_at")
class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    class Meta:
        model = Product
        fields = ("id", "user", "name", "brand", "category", "purchased_at", "image", "passport_code", "metadata", "created_at", "images")
        read_only_fields = ("user", "created_at")

class CareBookmarkSerializer(serializers.ModelSerializer):
    class Meta:
        model = CareBookmark
        fields = ("id", "guide_id", "created_at")
        read_only_fields = ("id", "created_at")
