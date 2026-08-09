from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from .models import Product


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
                "memo": "첫 명품",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["passport_code"].startswith("AURA-"))
        self.assertEqual(self.client.get("/api/products/").data[0]["id"], response.data["id"])

    def test_other_users_product_is_private(self):
        product = Product.objects.create(user=self.other, name="Private", category="bag")
        self.assertEqual(self.client.get(f"/api/products/{product.id}/").status_code, 404)
