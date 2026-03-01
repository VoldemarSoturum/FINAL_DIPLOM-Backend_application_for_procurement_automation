# apps/orders/views.py

from apps.users.permissions import IsClient
from apps.orders.services.emails import send_order_email_to_admin, send_order_email_to_customer

from django.db import transaction
from django.db.models import Prefetch
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import ProductInfo
from apps.orders.models import Order, OrderItem

from .serializers import (
    BasketSerializer,
    BasketItemAddSerializer,
    BasketItemUpdateSerializer,
)


def ok(data=None, http_status=status.HTTP_200_OK):
    return Response({"Status": True, "data": data, "errors": None}, status=http_status)


def fail(errors, http_status=status.HTTP_400_BAD_REQUEST):
    return Response({"Status": False, "data": None, "errors": errors}, status=http_status)


def _get_or_create_basket(user) -> Order:
    basket, _ = Order.objects.get_or_create(user=user, status=Order.Status.BASKET)
    return basket


def _basket_queryset(user):
    return (
        Order.objects.filter(user=user, status=Order.Status.BASKET)
        .prefetch_related(
            Prefetch(
                "items",
                queryset=OrderItem.objects.select_related("product", "shop"),
            )
        )
    )


class BasketAPIView(APIView):
    """
    GET /api/basket/
    """
    permission_classes = [IsAuthenticated, IsClient]

    @extend_schema(
        responses={200: OpenApiResponse(response=BasketSerializer)},
        examples=[
            OpenApiExample(
                "Unified success",
                value={"Status": True, "data": {"basket": {"id": 1, "status": "basket", "dt": "...", "items": []}}, "errors": None},
                response_only=True,
            )
        ],
    )
    def get(self, request, *args, **kwargs):
        _get_or_create_basket(request.user)
        basket = _basket_queryset(request.user).get()
        return ok({"basket": BasketSerializer(basket).data}, status.HTTP_200_OK)


class BasketItemsAPIView(APIView):
    """
    POST /api/basket/items/
    body: {"product_info_id": 123, "quantity": 2}
    """
    permission_classes = [IsAuthenticated, IsClient]

    @extend_schema(
        request=BasketItemAddSerializer,
        responses={
            200: OpenApiResponse(response=BasketSerializer),
            400: OpenApiResponse(description="Validation error"),
            404: OpenApiResponse(description="ProductInfo not found"),
            409: OpenApiResponse(description="Conflict (disabled shop/out of stock)"),
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = BasketItemAddSerializer(data=request.data)
        if not serializer.is_valid():
            return fail(serializer.errors, status.HTTP_400_BAD_REQUEST)

        product_info_id = serializer.validated_data["product_info_id"]
        qty = serializer.validated_data["quantity"]

        product_info = (
            ProductInfo.objects.select_related("product", "shop")
            .filter(id=product_info_id)
            .first()
        )
        if not product_info:
            return fail("ProductInfo not found", status.HTTP_404_NOT_FOUND)

        if not product_info.shop.state:
            return fail("Shop is disabled", status.HTTP_409_CONFLICT)

        if product_info.quantity <= 0:
            return fail("Out of stock", status.HTTP_409_CONFLICT)

        with transaction.atomic():
            basket = _get_or_create_basket(request.user)

            item, created = OrderItem.objects.get_or_create(
                order=basket,
                product=product_info.product,
                shop=product_info.shop,
                defaults={"quantity": qty},
            )
            if not created:
                item.quantity += qty
                item.save(update_fields=["quantity"])

        basket = _basket_queryset(request.user).get()
        return ok({"basket": BasketSerializer(basket).data}, status.HTTP_200_OK)


class BasketItemDetailAPIView(APIView):
    """
    PATCH /api/basket/items/{item_id}/
    DELETE /api/basket/items/{item_id}/
    """
    permission_classes = [IsAuthenticated, IsClient]

    @extend_schema(
        request=BasketItemUpdateSerializer,
        responses={200: OpenApiResponse(response=BasketSerializer), 404: OpenApiResponse(description="Not found")},
    )
    def patch(self, request, item_id: int, *args, **kwargs):
        serializer = BasketItemUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return fail(serializer.errors, status.HTTP_400_BAD_REQUEST)
        qty = serializer.validated_data["quantity"]

        basket = _get_or_create_basket(request.user)

        item = OrderItem.objects.filter(order=basket, id=item_id).first()
        if not item:
            return fail("Item not found in basket", status.HTTP_404_NOT_FOUND)

        item.quantity = qty
        item.save(update_fields=["quantity"])

        basket = _basket_queryset(request.user).get()
        return ok({"basket": BasketSerializer(basket).data}, status.HTTP_200_OK)

    @extend_schema(responses={200: OpenApiResponse(response=BasketSerializer), 404: OpenApiResponse(description="Not found")})
    def delete(self, request, item_id: int, *args, **kwargs):
        basket = _get_or_create_basket(request.user)

        item = OrderItem.objects.filter(order=basket, id=item_id).first()
        if not item:
            return fail("Item not found in basket", status.HTTP_404_NOT_FOUND)

        item.delete()

        basket = _basket_queryset(request.user).get()
        return ok({"basket": BasketSerializer(basket).data}, status.HTTP_200_OK)


class BasketCheckoutAPIView(APIView):
    """
    POST /api/basket/checkout/
    """
    permission_classes = [IsAuthenticated, IsClient]

    @extend_schema(
        responses={
            200: OpenApiResponse(response=BasketSerializer, description="Order created (basket -> new)"),
            404: OpenApiResponse(description="Basket not found"),
            409: OpenApiResponse(description="Basket empty / stock conflict / shop disabled"),
        }
    )
    def post(self, request, *args, **kwargs):
        basket = _basket_queryset(request.user).first()
        if not basket:
            _get_or_create_basket(request.user)
            return fail("Basket is empty", status.HTTP_409_CONFLICT)

        if not basket.items.exists():
            return fail("Basket is empty", status.HTTP_409_CONFLICT)

        with transaction.atomic():
            basket = (
                Order.objects.select_for_update()
                .filter(id=basket.id, user=request.user, status=Order.Status.BASKET)
                .prefetch_related(Prefetch("items", queryset=OrderItem.objects.select_related("product", "shop")))
                .first()
            )
            if not basket:
                return fail("Basket not found", status.HTTP_404_NOT_FOUND)

            items = list(basket.items.all())
            if not items:
                return fail("Basket is empty", status.HTTP_409_CONFLICT)

            product_ids = [i.product_id for i in items]
            shop_ids = [i.shop_id for i in items]

            infos = (
                ProductInfo.objects.select_for_update()
                .select_related("shop", "product")
                .filter(product_id__in=product_ids, shop_id__in=shop_ids)
            )

            info_map = {(pi.product_id, pi.shop_id): pi for pi in infos}

            for item in items:
                pi = info_map.get((item.product_id, item.shop_id))
                if not pi:
                    return fail(
                        f"ProductInfo not found for product={item.product_id} shop={item.shop_id}",
                        status.HTTP_409_CONFLICT,
                    )

                if not pi.shop.state:
                    return fail(f"Shop '{pi.shop.name}' is disabled", status.HTTP_409_CONFLICT)

                if pi.quantity < item.quantity:
                    return fail(
                        f"Not enough stock for '{pi.name}' (have {pi.quantity}, need {item.quantity})",
                        status.HTTP_409_CONFLICT,
                    )

            for item in items:
                pi = info_map[(item.product_id, item.shop_id)]

                item.unit_price = pi.price
                item.unit_price_rrc = pi.price_rrc
                item.save(update_fields=["unit_price", "unit_price_rrc"])

                pi.quantity -= item.quantity
                pi.save(update_fields=["quantity"])

            basket.status = Order.Status.NEW
            basket.save(update_fields=["status"])

        # Перечитаем заказ в статусе NEW (и используем его же и для ответа, и для email)
        order = (
            Order.objects.filter(id=basket.id)
            .prefetch_related(Prefetch("items", queryset=OrderItem.objects.select_related("product", "shop")))
            .select_related("user")
            .first()
        )

        if order is None:
            return fail("Order not found after checkout", status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            send_order_email_to_customer(order)
            send_order_email_to_admin(order)
        except Exception:
            # позже вынесем в celery + логирование
            pass

        return ok({"order": BasketSerializer(order).data}, status.HTTP_200_OK)


class ClientOrdersAPIView(APIView):
    """
    GET /api/orders/
    Returns orders of current user (excluding basket).
    """
    permission_classes = [IsAuthenticated, IsClient]

    @extend_schema(
        responses={200: OpenApiResponse(description="List of orders (unified)")},
        examples=[
            OpenApiExample(
                "Unified success",
                value={"Status": True, "data": {"orders": []}, "errors": None},
                response_only=True,
            )
        ],
    )
    def get(self, request, *args, **kwargs):
        qs = (
            Order.objects.filter(user=request.user)
            .exclude(status=Order.Status.BASKET)
            .prefetch_related(Prefetch("items", queryset=OrderItem.objects.select_related("product", "shop")))
            .order_by("-dt")
        )

        data = [
            {
                "id": o.id,
                "status": o.status,
                "dt": o.dt.isoformat(),
                "items": [
                    {
                        "id": i.id,
                        "product_id": i.product_id,
                        "product_name": i.product.name,
                        "shop_id": i.shop_id,
                        "shop_name": i.shop.name,
                        "quantity": i.quantity,
                        "unit_price": str(i.unit_price) if i.unit_price is not None else None,
                        "unit_price_rrc": str(i.unit_price_rrc) if i.unit_price_rrc is not None else None,
                    }
                    for i in o.items.all()
                ],
            }
            for o in qs
        ]

        return ok({"orders": data}, status.HTTP_200_OK)