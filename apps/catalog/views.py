from django.shortcuts import render

# Create your views here.

from django.db.models import Prefetch, Q
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import generics, filters
from rest_framework.permissions import AllowAny

from apps.catalog.models import Category, Shop, Product, ProductInfo, ProductParameter
from .serializers import CategorySerializer, ShopSerializer, ProductSerializer


def _product_queryset():
    """
    Оптимизированный queryset, чтобы не ловить N+1:
    Product -> category (select_related)
    Product -> product_infos (prefetch, с shop)
    ProductInfo -> parameters (prefetch, с parameter)
    """
    product_info_qs = (
        ProductInfo.objects.select_related("shop")
        .prefetch_related(
            Prefetch(
                "parameters",
                queryset=ProductParameter.objects.select_related("parameter"),
            )
        )
    )

    return (
        Product.objects.select_related("category")
        .prefetch_related(Prefetch("product_infos", queryset=product_info_qs))
    )


class CategoryListAPIView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = CategorySerializer
    queryset = Category.objects.all().order_by("name")


class ShopListAPIView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ShopSerializer
    queryset = Shop.objects.all().order_by("name")


@extend_schema(
    parameters=[
        OpenApiParameter(name="category", required=False, type=int, description="Category id"),
        OpenApiParameter(name="shop", required=False, type=int, description="Shop id"),
        OpenApiParameter(name="in_stock", required=False, type=int, description="1 -> only quantity > 0"),
        OpenApiParameter(name="q", required=False, type=str, description="Search (product name / offer name / model)"),
        OpenApiParameter(name="ordering", required=False, type=str, description="Ordering: name or -name"),
    ],
)
class ProductListAPIView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["name"]
    ordering = ["name"]

    def get_queryset(self):
        qs = _product_queryset()

        category_id = self.request.query_params.get("category")
        if category_id:
            qs = qs.filter(category_id=category_id)

        shop_id = self.request.query_params.get("shop")
        if shop_id:
            qs = qs.filter(product_infos__shop_id=shop_id)

        in_stock = self.request.query_params.get("in_stock")
        if in_stock == "1":
            qs = qs.filter(product_infos__quantity__gt=0)

        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(product_infos__name__icontains=q)
                | Q(product_infos__model__icontains=q)
            )

        # Чтобы список не раздувался от JOIN-ов
        return qs.distinct()


class ProductDetailAPIView(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductSerializer

    def get_queryset(self):
        return _product_queryset()