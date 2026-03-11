# apps/catalog/views.py

from django.db.models import Prefetch, Q
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from rest_framework import generics, filters, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from apps.catalog.models import Category, Shop, Product, ProductInfo, ProductParameter
from .serializers import (
    CategorySerializer,
    ShopSerializer,
    ProductSerializer,
    ProductImageUploadSerializer,
)


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


class ProductImageUploadAPIView(APIView):
    """
    PATCH /api/catalog/products/{id}/image/ (multipart/form-data)
    form-data:
      - image: <file>
    """
    permission_classes = [AllowAny]  # на этом шаге можно оставить так
    parser_classes = (MultiPartParser, FormParser)

    @extend_schema(
        request=ProductImageUploadSerializer,
        responses={
            200: OpenApiResponse(response=ProductSerializer, description="Product with uploaded image"),
            400: OpenApiResponse(description="Validation error"),
            404: OpenApiResponse(description="Product not found"),
        },
    )
    def patch(self, request, pk: int, *args, **kwargs):
        product = get_object_or_404(Product, pk=pk)

        serializer = ProductImageUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product.image = serializer.validated_data["image"]
        product.save(update_fields=["image"])

        # важно: передаём request в context, чтобы ImageField отдал абсолютный URL (если нужно)
        out = ProductSerializer(product, context={"request": request}).data
        return Response(out, status=status.HTTP_200_OK)