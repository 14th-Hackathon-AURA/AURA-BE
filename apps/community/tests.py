import base64

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from apps.accounts.models import Profile
from apps.catalog.models import Product
from .models import Comment, Post, PostImage


class CommunityApiTests(APITestCase):
    image_bytes = base64.b64decode("R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==")

    def setUp(self):
        self.author = User.objects.create_user("author", password="strong-pass-123")
        self.reader = User.objects.create_user("reader", password="strong-pass-123")
        Profile.objects.create(user=self.author, nickname="아기사자")
        Profile.objects.create(user=self.reader, nickname="독자")
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
        self.assertEqual(
            response.data["tagged_product_cards"],
            [{"id": self.product.id, "name": "Bag", "brand": ""}],
        )
        self.assertNotIn("image", response.data["tagged_product_cards"][0])

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

    def test_multiple_post_images(self):
        self.client.force_authenticate(self.author)
        post = Post.objects.create(author=self.author, title="여러 사진", body="사진 모음")
        for order in range(2):
            response = self.client.post(
                "/api/post-images/",
                {
                    "post": post.id,
                    "order": order,
                    "image": SimpleUploadedFile(
                        f"image-{order}.gif", self.image_bytes, content_type="image/gif"
                    ),
                },
                format="multipart",
            )
            self.assertEqual(response.status_code, 201)
        response = self.client.get(f"/api/posts/{post.id}/")
        self.assertEqual(len(response.data["images"]), 2)
        self.assertEqual(response.data["author_nickname"], "아기사자")

    def test_membership_tier_uses_both_post_and_comment_counts(self):
        posts = Post.objects.bulk_create(
            [Post(author=self.author, title=f"post-{index}", body="") for index in range(50)]
        )
        Comment.objects.bulk_create(
            [Comment(post=posts[0], author=self.author, body="comment") for _ in range(50)]
        )
        self.client.force_authenticate(self.reader)
        response = self.client.get(f"/api/posts/{posts[0].id}/")
        self.assertEqual(response.data["author_membership_tier"], "AURA Gold")
