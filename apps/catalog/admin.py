from django.contrib import admin
from .models import CareBookmark, Product, ProductImage

admin.site.register(Product)
admin.site.register(ProductImage)
admin.site.register(CareBookmark)
