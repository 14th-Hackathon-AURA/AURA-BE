from rest_framework import serializers
from apps.catalog.models import Product
from apps.accounts.models import calculate_membership_tier
from .models import Comment, Post, PostImage, PostLike


class PostImageSerializer(serializers.ModelSerializer):
    post = serializers.PrimaryKeyRelatedField(queryset=Post.objects.all(), write_only=True)

    class Meta:
        model = PostImage
        fields = ("id", "post", "image", "order", "created_at")
        read_only_fields = ("id", "created_at")

    def validate_post(self, post):
        if post.author_id != self.context["request"].user.id:
            raise serializers.ValidationError("본인 게시글에만 이미지를 추가할 수 있습니다.")
        return post


class CommentSerializer(serializers.ModelSerializer):
    author_nickname = serializers.SerializerMethodField()
    author_membership_tier = serializers.SerializerMethodField()

    def get_author_nickname(self, obj):
        profile = getattr(obj.author, "profile", None)
        return profile.nickname if profile and profile.nickname else obj.author.username

    def get_author_membership_tier(self, obj):
        return calculate_membership_tier(obj.author)

    class Meta:
        model = Comment
        fields = (
            "id", "post", "author", "author_nickname",
            "author_membership_tier", "body", "created_at",
        )
        read_only_fields = ("author", "created_at")
    def validate_post(self, post):
        if self.instance and self.instance.post_id != post.id:
            raise serializers.ValidationError("댓글의 게시글은 변경할 수 없습니다.")
        return post

class PostSerializer(serializers.ModelSerializer):
    comments = CommentSerializer(many=True, read_only=True)
    images = PostImageSerializer(many=True, read_only=True)
    like_count = serializers.IntegerField(source="likes.count", read_only=True)
    liked_by_me = serializers.SerializerMethodField()
    author_nickname = serializers.SerializerMethodField()
    author_membership_tier = serializers.SerializerMethodField()
    tagged_products = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Product.objects.all(), required=False
    )
    tagged_product_cards = serializers.SerializerMethodField()

    def get_author_nickname(self, obj):
        profile = getattr(obj.author, "profile", None)
        return profile.nickname if profile and profile.nickname else obj.author.username

    def get_author_membership_tier(self, obj):
        return calculate_membership_tier(obj.author)

    def get_liked_by_me(self, obj):
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and obj.likes.filter(user=request.user).exists())

    def get_tagged_product_cards(self, obj):
        return [
            {"id": product.id, "name": product.name, "brand": product.brand}
            for product in obj.tagged_products.all()
        ]

    def validate_tagged_products(self, products):
        request = self.context["request"]
        if any(product.user_id != request.user.id for product in products):
            raise serializers.ValidationError("본인이 등록한 제품만 태그할 수 있습니다.")
        return products

    class Meta:
        model = Post
        fields = (
            "id",
            "author",
            "author_nickname",
            "author_membership_tier",
            "title",
            "body",
            "image",
            "images",
            "created_at",
            "comments",
            "like_count",
            "liked_by_me",
            "tagged_products",
            "tagged_product_cards",
        )
        read_only_fields = ("author", "created_at")
class PostLikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostLike
        fields = ("id", "post", "created_at")
        read_only_fields = ("id", "created_at")

    def validate_post(self, post):
        request = self.context["request"]
        if PostLike.objects.filter(post=post, user=request.user).exists():
            raise serializers.ValidationError("이미 좋아요한 게시글입니다.")
        return post
