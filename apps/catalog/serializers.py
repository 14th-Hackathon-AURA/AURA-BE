from rest_framework import serializers

from apps.care.models import CareGuide

from .models import CareBookmark, Product, ProductImage


ALLOWED_DOCUMENT_EXTENSIONS = (".jpg", ".jpeg", ".png", ".pdf")
MAX_DOCUMENT_SIZE = 4 * 1024 * 1024  # Azure F0 기준 4MB


class ProductImageSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(
        write_only=True,
        queryset=Product.objects.all(),
    )

    class Meta:
        model = ProductImage
        fields = (
            "id",
            "product",
            "image",
            "kind",
            "is_receipt",
            "created_at",
        )
        read_only_fields = ("id", "created_at")

    def validate(self, attrs):
        product = attrs.get("product", getattr(self.instance, "product", None))
        request = self.context.get("request")

        if product and request and product.user_id != request.user.id:
            raise serializers.ValidationError(
                {"product": "본인 제품에만 파일을 등록할 수 있습니다."}
            )

        kind = attrs.get(
            "kind",
            getattr(self.instance, "kind", ProductImage.Kind.PRODUCT),
        )

        if attrs.get("is_receipt"):
            kind = ProductImage.Kind.RECEIPT

        attrs["kind"] = kind
        attrs["is_receipt"] = kind == ProductImage.Kind.RECEIPT

        return attrs


class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)

    # 제품 등록 화면에서 영수증·보증서를 한 번에 전송하기 위한 필드
    receipt_file = serializers.FileField(
        write_only=True,
        required=False,
        allow_null=True,
    )
    warranty_file = serializers.FileField(
        write_only=True,
        required=False,
        allow_null=True,
    )

    diagnosis_history = serializers.SerializerMethodField()
    service_history = serializers.SerializerMethodField()

    def validate_document_file(self, file):
        if not file:
            return file

        if not file.name.lower().endswith(ALLOWED_DOCUMENT_EXTENSIONS):
            raise serializers.ValidationError(
                "영수증·보증서는 JPG, JPEG, PNG, PDF만 업로드할 수 있습니다."
            )

        if file.size > MAX_DOCUMENT_SIZE:
            raise serializers.ValidationError(
                "영수증·보증서 파일은 4MB 이하만 업로드할 수 있습니다."
            )

        return file

    def validate_receipt_file(self, file):
        return self.validate_document_file(file)

    def validate_warranty_file(self, file):
        return self.validate_document_file(file)

    def create(self, validated_data):
        receipt_file = validated_data.pop("receipt_file", None)
        warranty_file = validated_data.pop("warranty_file", None)

        product = Product.objects.create(**validated_data)

        if receipt_file:
            ProductImage.objects.create(
                product=product,
                image=receipt_file,
                kind=ProductImage.Kind.RECEIPT,
                is_receipt=True,
            )

        if warranty_file:
            ProductImage.objects.create(
                product=product,
                image=warranty_file,
                kind=ProductImage.Kind.WARRANTY,
                is_receipt=False,
            )

        return product

    def update(self, instance, validated_data):
        receipt_file = validated_data.pop("receipt_file", None)
        warranty_file = validated_data.pop("warranty_file", None)

        product = super().update(instance, validated_data)

        if receipt_file:
            ProductImage.objects.create(
                product=product,
                image=receipt_file,
                kind=ProductImage.Kind.RECEIPT,
                is_receipt=True,
            )

        if warranty_file:
            ProductImage.objects.create(
                product=product,
                image=warranty_file,
                kind=ProductImage.Kind.WARRANTY,
                is_receipt=False,
            )

        return product

    def get_diagnosis_history(self, obj):
        return [
            {
                "id": diagnosis.id,
                "status": diagnosis.status,
                "condition_level": diagnosis.condition_level,
                "created_at": diagnosis.created_at,
            }
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
            "id",
            "user",
            "name",
            "brand",
            "category",
            "purchased_at",
            "purchase_place",
            "purchase_channel",
            "purchase_price",
            "memo",
            "image",
            "receipt_file",
            "warranty_file",
            "passport_code",
            "metadata",
            "created_at",
            "images",
            "diagnosis_history",
            "service_history",
        )
        read_only_fields = (
            "id",
            "user",
            "passport_code",
            "created_at",
        )


class CareBookmarkSerializer(serializers.ModelSerializer):
    class Meta:
        model = CareBookmark
        fields = ("id", "guide_id", "created_at")
        read_only_fields = ("id", "created_at")

    def validate_guide_id(self, value):
        if not CareGuide.objects.filter(
            id=value,
            is_published=True,
        ).exists():
            raise serializers.ValidationError(
                "조회 가능한 케어 가이드를 선택해 주세요."
            )

        return value