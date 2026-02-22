from django.urls import path
from .views import PartnerUpdateAPIView, PartnerStateAPIView, PartnerShopAPIView
urlpatterns = [
    path("update/", PartnerUpdateAPIView.as_view(), name="partner-update"),
    path("state/", PartnerStateAPIView.as_view(), name="partner-state"),
    path("shop/", PartnerShopAPIView.as_view(), name="partner-shop"),
]