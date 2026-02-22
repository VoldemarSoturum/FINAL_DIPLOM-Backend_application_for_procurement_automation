from django.urls import path
from .views import PartnerUpdateAPIView

urlpatterns = [
    path("update/", PartnerUpdateAPIView.as_view(), name="partner-update"),
]