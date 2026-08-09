from rest_framework import serializers
from .models import Comment, Post, PostLike
class CommentSerializer(serializers.ModelSerializer):
    class Meta: model, fields = Comment, ("id", "author", "body", "created_at")
    read_only_fields = ("author",)
class PostSerializer(serializers.ModelSerializer):
    comments = CommentSerializer(many=True, read_only=True)
    like_count = serializers.IntegerField(source="likes.count", read_only=True)

    class Meta:
        model = Post
        fields = (
            "id",
            "author",
            "title",
            "body",
            "image",
            "created_at",
            "comments",
            "like_count",
        )
        read_only_fields = ("author",)
class PostLikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostLike
        fields = ("id", "post", "created_at")
        read_only_fields = ("id", "created_at")
