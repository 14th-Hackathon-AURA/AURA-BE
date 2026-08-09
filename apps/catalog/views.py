from rest_framework import viewsets
from rest_framework import mixins
from .models import CareBookmark, Product, ProductImage
from .serializers import CareBookmarkSerializer, ProductImageSerializer, ProductSerializer
class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    def get_queryset(self): return Product.objects.filter(user=self.request.user).order_by("-created_at")
    def perform_create(self, serializer): serializer.save(user=self.request.user)

class ProductImageViewSet(viewsets.ModelViewSet):
    serializer_class = ProductImageSerializer
    def get_queryset(self): return ProductImage.objects.filter(product__user=self.request.user)
    def perform_create(self, serializer):
        product = Product.objects.get(id=self.request.data["product"], user=self.request.user)
        serializer.save(product=product)

class CareBookmarkViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    serializer_class = CareBookmarkSerializer
    def get_queryset(self): return CareBookmark.objects.filter(user=self.request.user)
    def perform_create(self, serializer): serializer.save(user=self.request.user)
