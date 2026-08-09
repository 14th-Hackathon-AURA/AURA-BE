from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from apps.catalog.models import Product
from .models import Comment, Post


class CommunityApiTests(APITestCase):
    def setUp(self):
        self.author = User.objects.create_user("author", password="strong-pass-123")
        self.reader = User.objects.create_user("reader", password="strong-pass-123")
        self.product = Product.objects.create(user=self.author, name="Bag", category="bag")

    def test_product_tag_comment_like_and_permissions(self):
        self.client.force_authenticate(self.author)
        response = self.client.post(
            "/api/posts/",
            {"title": "관리 팁", "body": "공유합니다", "tagged_products": [self.product.id]},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        post_id = response.data["id"]

        self.client.force_authenticate(self.reader)
        response = self.client.post(
            "/api/comments/", {"post": post_id, "body": "좋은 정보네요"}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Comment.objects.get().post_id, post_id)
        self.assertEqual(
            self.client.post("/api/post-likes/", {"post": post_id}, format="json").status_code,
            201,
        )
        self.assertEqual(
            self.client.post("/api/post-likes/", {"post": post_id}, format="json").status_code,
            400,
        )
        self.assertEqual(
            self.client.patch(f"/api/posts/{post_id}/", {"title": "탈취"}, format="json").status_code,
            403,
        )

    def test_cannot_tag_another_users_product(self):
        self.client.force_authenticate(self.reader)
        response = self.client.post(
            "/api/posts/",
            {"title": "잘못된 태그", "body": "", "tagged_products": [self.product.id]},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
