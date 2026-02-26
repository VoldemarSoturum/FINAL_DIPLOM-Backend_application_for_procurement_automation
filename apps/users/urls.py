from django.urls import path
from .views import RegisterAPIView

urlpatterns = [
    path("auth/register/", RegisterAPIView.as_view(), name="auth-register"),
]