from rest_framework import generics, permissions, viewsets
from rest_framework_simplejwt.views import TokenObtainPairView
from .models import Notification, Profile
from .serializers import EmailTokenSerializer, NotificationSerializer, RegisterSerializer, ProfileSerializer

class RegisterView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer

class EmailTokenView(TokenObtainPairView):
    permission_classes = [permissions.AllowAny]
    serializer_class = EmailTokenSerializer

class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    def get_object(self):
        return Profile.objects.get_or_create(user=self.request.user)[0]

class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    http_method_names = ("get", "patch", "head", "options")
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)
