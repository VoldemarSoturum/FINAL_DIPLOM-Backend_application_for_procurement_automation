# Create your views here.
from apps.orders.services.emails import send_order_email_to_admin, send_order_email_to_customer

from django.db import transaction
from django.db.models import Prefetch
from drf_spectacular.utils import extend_schema, OpenApiResponse
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
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiResponse(response=BasketSerializer)})
    def get(self, request, *args, **kwargs):
        _get_or_create_basket(request.user)
        basket = _basket_queryset(request.user).get()
        return Response(BasketSerializer(basket).data, status=status.HTTP_200_OK)


class BasketItemsAPIView(APIView):
    """
    POST /api/basket/items/
    body: {"product_info_id": 123, "quantity": 2}
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=BasketItemAddSerializer,
        responses={200: OpenApiResponse(response=BasketSerializer), 400: OpenApiResponse(description="Validation error")},
    )
    def post(self, request, *args, **kwargs):
        serializer = BasketItemAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product_info_id = serializer.validated_data["product_info_id"]
        qty = serializer.validated_data["quantity"]

        product_info = (
            ProductInfo.objects.select_related("product", "shop")
            .filter(id=product_info_id)
            .first()
        )
        if not product_info:
            return Response({"detail": "ProductInfo not found"}, status=status.HTTP_404_NOT_FOUND)

        if not product_info.shop.state:
            return Response({"detail": "Shop is disabled"}, status=status.HTTP_409_CONFLICT)

        if product_info.quantity <= 0:
            return Response({"detail": "Out of stock"}, status=status.HTTP_409_CONFLICT)

        with transaction.atomic():
            basket = _get_or_create_basket(request.user)

            item, created = OrderItem.objects.get_or_create(
                order=basket,
                product=product_info.product,
                shop=product_info.shop,
                defaults={
                    "quantity": qty,
                },
            )
            if not created:
                item.quantity += qty
                item.save(update_fields=["quantity"])

        basket = _basket_queryset(request.user).get()
        return Response(BasketSerializer(basket).data, status=status.HTTP_200_OK)


class BasketItemDetailAPIView(APIView):
    """
    PATCH /api/basket/items/{item_id}/
    DELETE /api/basket/items/{item_id}/
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=BasketItemUpdateSerializer,
        responses={200: OpenApiResponse(response=BasketSerializer)},
    )
    def patch(self, request, item_id: int, *args, **kwargs):
        serializer = BasketItemUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        qty = serializer.validated_data["quantity"]

        basket = _get_or_create_basket(request.user)

        item = OrderItem.objects.filter(order=basket, id=item_id).first()
        if not item:
            return Response({"detail": "Item not found in basket"}, status=status.HTTP_404_NOT_FOUND)

        item.quantity = qty
        item.save(update_fields=["quantity"])

        basket = _basket_queryset(request.user).get()
        return Response(BasketSerializer(basket).data, status=status.HTTP_200_OK)

    @extend_schema(responses={200: OpenApiResponse(response=BasketSerializer)})
    def delete(self, request, item_id: int, *args, **kwargs):
        basket = _get_or_create_basket(request.user)

        item = OrderItem.objects.filter(order=basket, id=item_id).first()
        if not item:
            return Response({"detail": "Item not found in basket"}, status=status.HTTP_404_NOT_FOUND)

        item.delete()

        basket = _basket_queryset(request.user).get()
        return Response(BasketSerializer(basket).data, status=status.HTTP_200_OK)

class BasketCheckoutAPIView(APIView):
    """
    POST /api/basket/checkout/
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: OpenApiResponse(response=BasketSerializer, description="Order created (basket -> new)"),
            409: OpenApiResponse(description="Basket empty / stock conflict / shop disabled"),
        }
    )
    def post(self, request, *args, **kwargs):
        basket = _basket_queryset(request.user).first()
        if not basket:
            # Корзины нет — создадим пустую и вернём конфликт (нечего оформлять)
            _get_or_create_basket(request.user)
            return Response({"detail": "Basket is empty"}, status=status.HTTP_409_CONFLICT)

        if not basket.items.exists():
            return Response({"detail": "Basket is empty"}, status=status.HTTP_409_CONFLICT)

        with transaction.atomic():
            # Перечитываем корзину внутри транзакции с items
            basket = (
                Order.objects.select_for_update()
                .filter(id=basket.id, user=request.user, status=Order.Status.BASKET)
                .prefetch_related(Prefetch("items", queryset=OrderItem.objects.select_related("product", "shop")))
                .first()
            )
            if not basket:
                return Response({"detail": "Basket not found"}, status=status.HTTP_404_NOT_FOUND)

            items = list(basket.items.all())
            if not items:
                return Response({"detail": "Basket is empty"}, status=status.HTTP_409_CONFLICT)

            # Считываем и блокируем все ProductInfo, которые нужны
            product_ids = [i.product_id for i in items]
            shop_ids = [i.shop_id for i in items]

            infos = (
                ProductInfo.objects.select_for_update()
                .select_related("shop", "product")
                .filter(product_id__in=product_ids, shop_id__in=shop_ids)
            )

            info_map = {(pi.product_id, pi.shop_id): pi for pi in infos}

            # Валидация перед списанием
            for item in items:
                pi = info_map.get((item.product_id, item.shop_id))
                if not pi:
                    return Response(
                        {"detail": f"ProductInfo not found for product={item.product_id} shop={item.shop_id}"},
                        status=status.HTTP_409_CONFLICT,
                    )

                if not pi.shop.state:
                    return Response(
                        {"detail": f"Shop '{pi.shop.name}' is disabled"},
                        status=status.HTTP_409_CONFLICT,
                    )

                if pi.quantity < item.quantity:
                    return Response(
                        {"detail": f"Not enough stock for '{pi.name}' (have {pi.quantity}, need {item.quantity})"},
                        status=status.HTTP_409_CONFLICT,
                    )

            # Списание и фиксация цен
            for item in items:
                pi = info_map[(item.product_id, item.shop_id)]

                item.unit_price = pi.price
                item.unit_price_rrc = pi.price_rrc
                item.save(update_fields=["unit_price", "unit_price_rrc"])

                pi.quantity -= item.quantity
                pi.save(update_fields=["quantity"])

            basket.status = Order.Status.NEW
            basket.save(update_fields=["status"])

        # Возвращаем уже оформленный заказ
        basket = (
            Order.objects.filter(id=basket.id)
            .prefetch_related(Prefetch("items", queryset=OrderItem.objects.select_related("product", "shop")))
            .first()
        )
        # Перечитаем заказ уже в статусе NEW вместе с items для письма
        order = (
            Order.objects.filter(id=basket.id)
            .prefetch_related(Prefetch("items", queryset=OrderItem.objects.select_related("product", "shop")))
            .select_related("user")
            .first()
        )

        # Email notifications (sync, base part)
        try:
            send_order_email_to_customer(order)
            send_order_email_to_admin(order)
        except Exception as e:
            # На базовой части можно не падать из-за email.
            # Для продакшена — логирование + celery. To be Continued in next commits:)
            pass
        return Response(BasketSerializer(basket).data, status=status.HTTP_200_OK)