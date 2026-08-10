from rest_framework import mixins, viewsets
from rest_framework.exceptions import PermissionDenied
from .models import Comment, Post, PostImage, PostLike
from .serializers import CommentSerializer, PostImageSerializer, PostLikeSerializer, PostSerializer
class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all().select_related("author", "author__profile").prefetch_related(
        "comments__author__profile", "images", "likes", "tagged_products"
    ).order_by("-created_at")
    serializer_class = PostSerializer
    def perform_create(self, serializer): serializer.save(author=self.request.user)
    def perform_update(self, serializer):
        if serializer.instance.author != self.request.user: raise PermissionDenied("작성자만 수정할 수 있습니다.")
        serializer.save()
    def perform_destroy(self, instance):
        if instance.author != self.request.user: raise PermissionDenied("작성자만 삭제할 수 있습니다.")
        instance.delete()

class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    def get_queryset(self): return Comment.objects.filter(post_id=self.request.query_params.get("post")).order_by("created_at")
    def perform_create(self, serializer): serializer.save(author=self.request.user)
    def perform_update(self, serializer):
        if serializer.instance.author != self.request.user: raise PermissionDenied("작성자만 수정할 수 있습니다.")
        serializer.save()
    def perform_destroy(self, instance):
        if instance.author != self.request.user: raise PermissionDenied("작성자만 삭제할 수 있습니다.")
        instance.delete()

class PostLikeViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    serializer_class = PostLikeSerializer
    def get_queryset(self): return PostLike.objects.filter(user=self.request.user)
    def perform_create(self, serializer): serializer.save(user=self.request.user)


class PostImageViewSet(viewsets.ModelViewSet):
    serializer_class = PostImageSerializer

    def get_queryset(self):
        queryset = PostImage.objects.select_related("post", "post__author")
        post_id = self.request.query_params.get("post")
        return queryset.filter(post_id=post_id) if post_id else queryset

    def perform_update(self, serializer):
        if serializer.instance.post.author_id != self.request.user.id:
            raise PermissionDenied("작성자만 이미지를 수정할 수 있습니다.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.post.author_id != self.request.user.id:
            raise PermissionDenied("작성자만 이미지를 삭제할 수 있습니다.")
        instance.delete()
