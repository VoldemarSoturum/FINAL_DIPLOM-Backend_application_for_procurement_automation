# apps/catalog/urls.py

from django.urls import path

from .views import (
    CategoryListAPIView,
    ShopListAPIView,
    ProductListAPIView,
    ProductDetailAPIView,
    ProductImageUploadAPIView,
)

urlpatterns = [
    path("categories/", CategoryListAPIView.as_view(), name="catalog-categories"),
    path("shops/", ShopListAPIView.as_view(), name="catalog-shops"),
    path("products/", ProductListAPIView.as_view(), name="catalog-products"),
    path("products/<int:pk>/", ProductDetailAPIView.as_view(), name="catalog-product-detail"),
    path("products/<int:pk>/image/", ProductImageUploadAPIView.as_view(), name="catalog-product-image"),
]