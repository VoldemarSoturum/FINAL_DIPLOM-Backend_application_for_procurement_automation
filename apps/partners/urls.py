from django.urls import path
from .views import PartnerUpdateAPIView, PartnerStateAPIView
urlpatterns = [
    path("update/", PartnerUpdateAPIView.as_view(), name="partner-update"),
    path("state/", PartnerStateAPIView.as_view(), name="partner-state"),
]