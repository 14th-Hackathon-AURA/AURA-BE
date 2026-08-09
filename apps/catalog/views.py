from rest_framework import viewsets
from rest_framework import mixins
from .models import CareBookmark, Product, ProductImage
from .serializers import CareBookmarkSerializer, ProductImageSerializer, ProductSerializer
class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    def get_queryset(self):
        return Product.objects.filter(user=self.request.user).prefetch_related("images", "diagnoses").order_by("-created_at")
    def perform_create(self, serializer): serializer.save(user=self.request.user)

class ProductImageViewSet(viewsets.ModelViewSet):
    serializer_class = ProductImageSerializer
    def get_queryset(self): return ProductImage.objects.filter(product__user=self.request.user)
    def perform_create(self, serializer):
        product = serializer.validated_data["product"]
        if product.user != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("본인 제품에만 이미지를 등록할 수 있습니다.")
        serializer.save(product=product)

class CareBookmarkViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    serializer_class = CareBookmarkSerializer
    def get_queryset(self): return CareBookmark.objects.filter(user=self.request.user)
    def perform_create(self, serializer): serializer.save(user=self.request.user)
