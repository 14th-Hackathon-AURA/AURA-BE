from rest_framework import serializers
from .models import CareBookmark, Product, ProductImage
class ProductImageSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(write_only=True, queryset=Product.objects.all())

    class Meta:
        model = ProductImage
        fields = ("id", "product", "image", "kind", "is_receipt", "created_at")
        read_only_fields = ("id", "created_at")
    def validate(self, attrs):
        if attrs.get("is_receipt") and attrs.get("kind", ProductImage.Kind.PRODUCT) == ProductImage.Kind.PRODUCT:
            attrs["kind"] = ProductImage.Kind.RECEIPT
        return attrs
class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    diagnosis_history = serializers.SerializerMethodField()
    def get_diagnosis_history(self, obj):
        return [
            {"id": diagnosis.id, "status": diagnosis.status, "condition_level": diagnosis.condition_level, "created_at": diagnosis.created_at}
            for diagnosis in obj.diagnoses.all().order_by("-created_at")
        ]
    class Meta:
        model = Product
        fields = (
            "id", "user", "name", "brand", "category", "purchased_at",
            "purchase_place", "purchase_channel", "memo", "image",
            "passport_code", "metadata", "created_at", "images", "diagnosis_history",
        )
        read_only_fields = ("user", "passport_code", "created_at")

class CareBookmarkSerializer(serializers.ModelSerializer):
    class Meta:
        model = CareBookmark
        fields = ("id", "guide_id", "created_at")
        read_only_fields = ("id", "created_at")
