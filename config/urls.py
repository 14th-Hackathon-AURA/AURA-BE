from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from apps.accounts.views import EmailOrUsernameTokenView, NotificationViewSet, RegisterView, ProfileView
from apps.catalog.views import CareBookmarkViewSet, ProductImageViewSet, ProductViewSet
from apps.care.views import CareGuideViewSet, DiagnosisViewSet, ServiceRequestViewSet, StoreViewSet, VisitReservationViewSet
from apps.community.views import CommentViewSet, PostLikeViewSet, PostViewSet
from apps.ai.views import ChatView, CareRecommendationView, ChatSessionViewSet

router = DefaultRouter()
router.register("products", ProductViewSet, basename="product")
router.register("product-images", ProductImageViewSet, basename="product-image")
router.register("care-bookmarks", CareBookmarkViewSet, basename="care-bookmark")
router.register("diagnoses", DiagnosisViewSet, basename="diagnosis")
router.register("care-guides", CareGuideViewSet, basename="care-guide")
router.register("stores", StoreViewSet, basename="store")
router.register("visit-reservations", VisitReservationViewSet, basename="visit-reservation")
router.register("service-requests", ServiceRequestViewSet, basename="service-request")
router.register("posts", PostViewSet, basename="post")
router.register("comments", CommentViewSet, basename="comment")
router.register("post-likes", PostLikeViewSet, basename="post-like")
router.register("notifications", NotificationViewSet, basename="notification")
router.register("ai/chat-sessions", ChatSessionViewSet, basename="chat-session")
urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/register/", RegisterView.as_view()),
    path("api/auth/token/", EmailOrUsernameTokenView.as_view()), path("api/auth/token/refresh/", TokenRefreshView.as_view()),
    path("api/me/", ProfileView.as_view()), path("api/ai/chat/", ChatView.as_view()),
    path("api/ai/care-recommendations/", CareRecommendationView.as_view()), path("api/", include(router.urls)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
