from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import RegisterAPIView, ContactListCreateAPIView, ContactDetailAPIView, ProfileAvatarUploadAPIView

from .social_api import SocialApiLoginAPIView, SocialApiCompleteAPIView

urlpatterns = [
    path("auth/register/", RegisterAPIView.as_view(), name="auth-register"),
    path("auth/login/", TokenObtainPairView.as_view(), name="auth-login"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="auth-token-refresh"),

    path("contacts/", ContactListCreateAPIView.as_view(), name="contacts"),
    path("contacts/<int:contact_id>/", ContactDetailAPIView.as_view(), name="contact-detail"),

    # API-first Social Auth (JWT)
    path("auth/social/api/login/<str:backend>/", SocialApiLoginAPIView.as_view(), name="social-api-login"),
    path("auth/social/api/complete/<str:backend>/", SocialApiCompleteAPIView.as_view(), name="social-api-complete"),

    path("profile/avatar/", ProfileAvatarUploadAPIView.as_view()),
]