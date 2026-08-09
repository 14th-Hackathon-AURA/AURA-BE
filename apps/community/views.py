from rest_framework import mixins, viewsets
from rest_framework.exceptions import PermissionDenied
from .models import Comment, Post, PostLike
from .serializers import CommentSerializer, PostLikeSerializer, PostSerializer
class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all().select_related("author").prefetch_related("comments", "likes", "tagged_products").order_by("-created_at")
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
