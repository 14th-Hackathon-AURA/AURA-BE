from rest_framework import serializers

from apps.care.models import CareGuide

from .models import CareBookmark, Product, ProductImage
class ProductImageSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(write_only=True, queryset=Product.objects.all())

    class Meta:
        model = ProductImage
        fields = ("id", "product", "image", "kind", "is_receipt", "created_at")
        read_only_fields = ("id", "created_at")
    def validate(self, attrs):
        product = attrs.get("product", getattr(self.instance, "product", None))
        request = self.context.get("request")
        if product and request and product.user_id != request.user.id:
            raise serializers.ValidationError(
                {"product": "본인 제품에만 이미지를 등록할 수 있습니다."}
            )
        if attrs.get("is_receipt") and attrs.get("kind", ProductImage.Kind.PRODUCT) == ProductImage.Kind.PRODUCT:
            attrs["kind"] = ProductImage.Kind.RECEIPT
        return attrs
class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    diagnosis_history = serializers.SerializerMethodField()
    service_history = serializers.SerializerMethodField()
    def get_diagnosis_history(self, obj):
        return [
            {"id": diagnosis.id, "status": diagnosis.status, "condition_level": diagnosis.condition_level, "created_at": diagnosis.created_at}
            for diagnosis in obj.diagnoses.all().order_by("-created_at")
        ]

    def get_service_history(self, obj):
        return [
            {
                "id": request.id,
                "status": request.status,
                "symptom": request.symptom,
                "store_id": request.store_id,
                "created_at": request.created_at,
            }
            for request in obj.service_requests.all().order_by("-created_at")
        ]
    class Meta:
        model = Product
        fields = (
            "id", "user", "name", "brand", "category", "purchased_at",
            "purchase_place", "purchase_channel", "purchase_price", "memo", "image",
            "passport_code", "metadata", "created_at", "images",
            "diagnosis_history", "service_history",
        )
        read_only_fields = ("user", "passport_code", "created_at")

class CareBookmarkSerializer(serializers.ModelSerializer):
    class Meta:
        model = CareBookmark
        fields = ("id", "guide_id", "created_at")
        read_only_fields = ("id", "created_at")

    def validate_guide_id(self, value):
        if not CareGuide.objects.filter(id=value, is_published=True).exists():
            raise serializers.ValidationError("조회 가능한 케어 가이드를 선택해 주세요.")
        return value
