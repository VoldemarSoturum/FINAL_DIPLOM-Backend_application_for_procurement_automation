from django.urls import path
from .views import BasketAPIView, BasketItemsAPIView, BasketItemDetailAPIView, BasketCheckoutAPIView, \
    ClientOrdersAPIView

urlpatterns = [
    path("basket/", BasketAPIView.as_view(), name="basket"),
    path("basket/items/", BasketItemsAPIView.as_view(), name="basket-items"),
    path("basket/items/<int:item_id>/", BasketItemDetailAPIView.as_view(), name="basket-item-detail"),
    path("basket/checkout/", BasketCheckoutAPIView.as_view(), name="basket-checkout"),
    path("orders/", ClientOrdersAPIView.as_view(), name="client-orders"),
]