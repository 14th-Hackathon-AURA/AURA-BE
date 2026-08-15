from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from apps.care.models import CareGuide

from .models import Product, ProductImage


class ProductApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("owner", password="strong-pass-123")
        self.other = User.objects.create_user("other", password="strong-pass-123")
        self.client.force_authenticate(self.user)

    def test_product_crud_and_auto_passport(self):
        response = self.client.post(
            "/api/products/",
            {
                "name": "Leather Bag",
                "brand": "MCM",
                "category": "bag",
                "purchase_place": "청담 플래그십",
                "purchase_channel": "OFFLINE",
                "purchase_price": 430000,
                "memo": "첫 명품",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["passport_code"].startswith("AURA-"))
        self.assertEqual(response.data["purchase_price"], 430000)
        self.assertEqual(self.client.get("/api/products/").data[0]["id"], response.data["id"])

    def test_other_users_product_is_private(self):
        product = Product.objects.create(user=self.other, name="Private", category="bag")
        self.assertEqual(self.client.get(f"/api/products/{product.id}/").status_code, 404)

    def test_purchase_channel_rejects_unknown_value(self):
        response = self.client.post(
            "/api/products/",
            {"name": "Bag", "category": "bag", "purchase_channel": "UNKNOWN"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_product_image_cannot_be_moved_to_another_users_product(self):
        owned = Product.objects.create(user=self.user, name="Owned", category="bag")
        private = Product.objects.create(user=self.other, name="Private", category="bag")
        image = ProductImage.objects.create(
            product=owned,
            image=SimpleUploadedFile("product.gif", b"GIF89a", content_type="image/gif"),
        )
        response = self.client.patch(
            f"/api/product-images/{image.id}/",
            {"product": private.id},
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)

    def test_bookmark_requires_published_guide(self):
        guide = CareGuide.objects.create(
            title="가죽 관리",
            material="가죽",
            content="마른 천으로 닦아 주세요.",
            is_published=False,
        )
        response = self.client.post(
            "/api/care-bookmarks/", {"guide_id": guide.id}, format="json"
        )
        self.assertEqual(response.status_code, 400)
