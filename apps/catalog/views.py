from django.shortcuts import get_object_or_404

from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from .models import CareBookmark, Product, ProductImage
from .serializers import (
    CareBookmarkSerializer,
    ProductImageSerializer,
    ProductSerializer,
)
from .services import (
    extract_receipt_information,
    extract_warranty_information,
)


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        return (
            Product.objects.filter(user=self.request.user)
            .prefetch_related(
                "images",
                "diagnoses",
                "service_requests",
            )
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=["post"], url_path="extract-document")
    def extract_document(self, request):
        """
        영수증/보증서 업로드 직후 호출하는 임시 분석 API.
        Product는 아직 생성하지 않습니다.
        """
        document = request.FILES.get("document")
        document_type = request.data.get("document_type")

        if not document:
            return Response(
                {"detail": "document 파일을 첨부해주세요."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if document_type not in ("receipt", "warranty"):
            return Response(
                {"detail": "document_type은 receipt 또는 warranty여야 합니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        allowed_extensions = (".jpg", ".jpeg", ".png", ".pdf")

        if not document.name.lower().endswith(allowed_extensions):
            return Response(
                {
                    "detail": (
                        "영수증·보증서는 JPG, JPEG, PNG, PDF만 "
                        "업로드할 수 있습니다."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if document.size > 4 * 1024 * 1024:
            return Response(
                {"detail": "무료 F0 기준으로 파일은 4MB 이하만 업로드할 수 있습니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            file_bytes = document.read()

            if document_type == "receipt":
                data = extract_receipt_information(file_bytes)
            else:
                data = extract_warranty_information(file_bytes)

        except Exception:
            # 분석 실패해도 제품 등록 화면은 계속 진행할 수 있어야 합니다.
            data = {
                "brand": None,
                "name": None,
                "purchased_at": None,
                "purchase_place": None,
                "purchase_price": None,
            }

            return Response(
                {
                    "success": False,
                    "detail": "문서를 분석하지 못했습니다. 직접 입력해주세요.",
                    "data": data,
                    "manual_input_required": [
                        "brand",
                        "name",
                        "purchased_at",
                        "purchase_place",
                    ],
                },
                status=status.HTTP_200_OK,
            )

        manual_fields = [
            field
            for field in (
                "brand",
                "name",
                "purchased_at",
                "purchase_place",
            )
            if not data.get(field)
        ]

        return Response(
            {
                "success": True,
                "document_type": document_type,
                "data": data,
                "manual_input_required": manual_fields,
            }
        )


class ProductImageViewSet(viewsets.ModelViewSet):
    serializer_class = ProductImageSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        return ProductImage.objects.filter(
            product__user=self.request.user
        ).order_by("-created_at")

    def perform_create(self, serializer):
        product_id = self.request.data.get("product")

        product = get_object_or_404(
            Product,
            id=product_id,
            user=self.request.user,
        )

        serializer.save(product=product)


class CareBookmarkViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = CareBookmarkSerializer

    def get_queryset(self):
        return CareBookmark.objects.filter(
            user=self.request.user
        ).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)