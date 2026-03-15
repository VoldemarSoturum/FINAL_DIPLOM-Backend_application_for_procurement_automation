# apps/orders/views.py
#
# Здесь живут APIViews для корзины и заказов клиента.
# Формат ответов единый: {"Status": bool, "data": ..., "errors": ...}
#
# Stage 9.7 (django-silk):
# - Добавлены 2 "profile блока" в ClientOrdersAPIView.get:
#   1) ORM fetch (реальное выполнение SQL + prefetch)
#   2) Python build response (сборка payload в Python)
#
# Важно:
# - QuerySet в Django ленивый. "Построение queryset" НЕ выполняет SQL.
# - Чтобы Silk показал время и количество запросов, нужно "материализовать" qs: list(qs)
#
from __future__ import annotations

from django.conf import settings
from django.db import transaction
from django.db.models import Prefetch
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import ProductInfo
from apps.orders.models import Order, OrderItem
from apps.orders.services.emails import send_order_email_to_admin, send_order_email_to_customer
from apps.orders.tasks import send_order_emails_task
from apps.users.permissions import IsClient

from .serializers import BasketItemAddSerializer, BasketItemUpdateSerializer, BasketSerializer


# -----------------------------------------------------------------------------
# Silk profiling (Stage 9.7)
# -----------------------------------------------------------------------------
# Требование:
# - В dev хотим профилировать код (Silk включён через env SILK_ENABLED=1).
# - В prod Silk обычно выключают => импорт должен быть безопасным.
# - Если silk не установлен / отключён — код не должен падать.
try:
    from silk.profiling.profiler import silk_profile  # type: ignore
except Exception:  # pragma: no cover
    # Фоллбек: context manager, который ничего не делает.
    from contextlib import contextmanager

    @contextmanager
    def silk_profile(*args, **kwargs):
        yield


# -----------------------------------------------------------------------------
# Unified response helpers
# -----------------------------------------------------------------------------
def ok(data=None, http_status=status.HTTP_200_OK):
    """
    Единый формат успеха.

    Пример:
    {
      "Status": true,
      "data": {...},
      "errors": null
    }
    """
    return Response({"Status": True, "data": data, "errors": None}, status=http_status)


def fail(errors, http_status=status.HTTP_400_BAD_REQUEST):
    """
    Единый формат ошибки.

    Пример:
    {
      "Status": false,
      "data": null,
      "errors": "..."
    }
    """
    return Response({"Status": False, "data": None, "errors": errors}, status=http_status)


# -----------------------------------------------------------------------------
# Basket helpers
# -----------------------------------------------------------------------------
def _get_or_create_basket(user) -> Order:
    """
    Гарантируем существование корзины:
    Order со статусом BASKET для текущего пользователя.
    """
    basket, _ = Order.objects.get_or_create(user=user, status=Order.Status.BASKET)
    return basket


def _basket_queryset(user):
    """
    Оптимизированный queryset корзины (защита от N+1):

    - prefetch_related("items") => вычитываем OrderItem одним запросом
    - OrderItem.select_related("product", "shop") => product и shop одним JOIN
      (иначе при сериализации items словим N+1 на item.product / item.shop)
    """
    return (
        Order.objects.filter(user=user, status=Order.Status.BASKET).prefetch_related(
            Prefetch(
                "items",
                queryset=OrderItem.objects.select_related("product", "shop"),
            )
        )
    )


# -----------------------------------------------------------------------------
# Basket endpoints
# -----------------------------------------------------------------------------
class BasketAPIView(APIView):
    """
    GET /api/basket/
    Возвращает корзину пользователя (создаёт при отсутствии).
    """
    permission_classes = [IsAuthenticated, IsClient]

    @extend_schema(
        responses={200: OpenApiResponse(response=BasketSerializer)},
        examples=[
            OpenApiExample(
                "Unified success",
                value={
                    "Status": True,
                    "data": {"basket": {"id": 1, "status": "basket", "dt": "...", "items": []}},
                    "errors": None,
                },
                response_only=True,
            )
        ],
    )
    def get(self, request, *args, **kwargs):
        # Корзина должна существовать
        _get_or_create_basket(request.user)

        # Подтягиваем корзину + items одним заходом (_basket_queryset уже оптимизирован)
        basket = _basket_queryset(request.user).get()
        return ok({"basket": BasketSerializer(basket).data}, status.HTTP_200_OK)


class BasketItemsAPIView(APIView):
    """
    POST /api/basket/items/
    body: {"product_info_id": 123, "quantity": 2}

    Логика:
    - валидируем вход
    - проверяем, что оффер существует, магазин включен, есть остаток
    - в транзакции добавляем/увеличиваем позицию в корзине
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

        # Берём ProductInfo и сразу подтягиваем product+shop (чтобы избежать N+1)
        product_info = (
            ProductInfo.objects.select_related("product", "shop").filter(id=product_info_id).first()
        )
        if not product_info:
            return fail("ProductInfo not found", status.HTTP_404_NOT_FOUND)

        # Бизнес-валидации: магазин должен принимать заказы
        if not product_info.shop.state:
            return fail("Shop is disabled", status.HTTP_409_CONFLICT)

        # Бизнес-валидация: должен быть остаток
        if product_info.quantity <= 0:
            return fail("Out of stock", status.HTTP_409_CONFLICT)

        # Все изменения корзины делаем в транзакции
        with transaction.atomic():
            basket = _get_or_create_basket(request.user)

            # Корзина хранит позиции по (order, product, shop)
            item, created = OrderItem.objects.get_or_create(
                order=basket,
                product=product_info.product,
                shop=product_info.shop,
                defaults={"quantity": qty},
            )
            if not created:
                # Если такая позиция уже была — увеличиваем количество
                item.quantity += qty
                item.save(update_fields=["quantity"])

        # Отдаём актуальную корзину
        basket = _basket_queryset(request.user).get()
        return ok({"basket": BasketSerializer(basket).data}, status.HTTP_200_OK)


class BasketItemDetailAPIView(APIView):
    """
    PATCH /api/basket/items/{item_id}/
    DELETE /api/basket/items/{item_id}/

    PATCH:
    - обновляет quantity (partial update)

    DELETE:
    - удаляет позицию из корзины
    """
    permission_classes = [IsAuthenticated, IsClient]

    @extend_schema(
        request=BasketItemUpdateSerializer,
        responses={
            200: OpenApiResponse(response=BasketSerializer),
            404: OpenApiResponse(description="Not found"),
        },
    )
    def patch(self, request, item_id: int, *args, **kwargs):
        serializer = BasketItemUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return fail(serializer.errors, status.HTTP_400_BAD_REQUEST)

        qty = serializer.validated_data["quantity"]
        basket = _get_or_create_basket(request.user)

        # Меняем только позицию, которая принадлежит корзине пользователя
        item = OrderItem.objects.filter(order=basket, id=item_id).first()
        if not item:
            return fail("Item not found in basket", status.HTTP_404_NOT_FOUND)

        item.quantity = qty
        item.save(update_fields=["quantity"])

        basket = _basket_queryset(request.user).get()
        return ok({"basket": BasketSerializer(basket).data}, status.HTTP_200_OK)

    @extend_schema(
        responses={
            200: OpenApiResponse(response=BasketSerializer),
            404: OpenApiResponse(description="Not found"),
        }
    )
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

    Задача:
    - превратить корзину (BASKET) в заказ (NEW)
    - зафиксировать цену на момент покупки
    - списать остатки ProductInfo.quantity (под блокировкой)
    - поставить отправку email в очередь (Celery) после commit (в prod)
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
        # Быстрый pre-check: без select_for_update (быстрее, но "без гарантий")
        basket = _basket_queryset(request.user).first()
        if not basket:
            # Корзину создаём, чтобы в системе было единообразно
            _get_or_create_basket(request.user)
            return fail("Basket is empty", status.HTTP_409_CONFLICT)

        if not basket.items.exists():
            return fail("Basket is empty", status.HTTP_409_CONFLICT)

        with transaction.atomic():
            # В транзакции берём basket под select_for_update,
            # чтобы не допустить параллельный checkout одной и той же корзины.
            basket = (
                Order.objects.select_for_update()
                .filter(id=basket.id, user=request.user, status=Order.Status.BASKET)
                .prefetch_related(
                    Prefetch(
                        "items",
                        queryset=OrderItem.objects.select_related("product", "shop"),
                    )
                )
                .first()
            )
            if not basket:
                return fail("Basket not found", status.HTTP_404_NOT_FOUND)

            items = list(basket.items.all())
            if not items:
                return fail("Basket is empty", status.HTTP_409_CONFLICT)

            # Списки для выборки ProductInfo одной пачкой
            product_ids = [i.product_id for i in items]
            shop_ids = [i.shop_id for i in items]

            # Блокируем ProductInfo (остатки) на время проверки и списания
            infos = (
                ProductInfo.objects.select_for_update()
                .select_related("shop", "product")
                .filter(product_id__in=product_ids, shop_id__in=shop_ids)
            )
            info_map = {(pi.product_id, pi.shop_id): pi for pi in infos}

            # 1) Проверяем, что всё доступно и остатков хватает
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

            # 2) Фиксируем цену + списываем остатки
            for item in items:
                pi = info_map[(item.product_id, item.shop_id)]

                # Снапшот цены "на момент покупки"
                item.unit_price = pi.price
                item.unit_price_rrc = pi.price_rrc
                item.save(update_fields=["unit_price", "unit_price_rrc"])

                # Списание остатков
                pi.quantity -= item.quantity
                pi.save(update_fields=["quantity"])

            # 3) Корзина становится заказом
            basket.status = Order.Status.NEW
            basket.save(update_fields=["status"])
            order_id = basket.id

            # 4) В prod: ставим отправку писем в очередь ПОСЛЕ commit
            if not getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
                transaction.on_commit(lambda: send_order_emails_task.delay(order_id))

        # Перечитываем заказ для ответа (уже NEW)
        order = (
            Order.objects.filter(id=order_id)
            .prefetch_related(
                Prefetch("items", queryset=OrderItem.objects.select_related("product", "shop"))
            )
            .select_related("user")
            .first()
        )
        if order is None:
            return fail("Order not found after checkout", status.HTTP_500_INTERNAL_SERVER_ERROR)

        # В eager режиме (tests/dev): отправляем письма синхронно, чтобы тесты видели mail.outbox
        if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
            try:
                send_order_email_to_customer(order)
                send_order_email_to_admin(order)
            except Exception:
                # В будущем можно заменить на logger.exception(...)
                pass

        return ok({"order": BasketSerializer(order).data}, status.HTTP_200_OK)


# -----------------------------------------------------------------------------
# Client orders endpoint (profiling target for Stage 9.7)
# -----------------------------------------------------------------------------
class ClientOrdersAPIView(APIView):
    """
    GET /api/orders/
    Возвращает заказы текущего пользователя (кроме корзины).

    Почему это хорошая точка для профилирования (Silk):
    - есть ORM часть (fetch + prefetch)
    - есть Python часть (сбор вложенного ответа)
    - на больших объёмах "build response" может стать bottleneck,
      даже если SQL оптимизирован.
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
        # ---------------------------------------------------------------------
        # 0) Готовим queryset (ЛЕНИВЫЙ => SQL ещё НЕ выполняется)
        # ---------------------------------------------------------------------
        qs = (
            Order.objects.filter(user=request.user)
            .exclude(status=Order.Status.BASKET)
            # prefetch items одним запросом, внутри items join product+shop (select_related)
            .prefetch_related(
                Prefetch("items", queryset=OrderItem.objects.select_related("product", "shop"))
            )
            .order_by("-dt")
        )

        # ---------------------------------------------------------------------
        # 1) Silk профиль: ORM fetch (ЗДЕСЬ реально выполняется SQL)
        # ---------------------------------------------------------------------
        # Важно понимать: "построение queryset" не даёт реального SQL-времени.
        # Нужно материализовать qs, чтобы:
        # - выполнился запрос на orders
        # - выполнился запрос на items (prefetch) с select_related(product, shop)
        with silk_profile(name="ClientOrdersAPIView.get: ORM fetch (orders + items prefetch)"):
            orders = list(qs)

        # ---------------------------------------------------------------------
        # 2) Silk профиль: Python build response (сборка payload)
        # ---------------------------------------------------------------------
        # Здесь SQL быть НЕ должно (если prefetch сработал),
        # а время уходит на Python циклы и сериализацию в dict.
        with silk_profile(name="ClientOrdersAPIView.get: Python build response"):
            data = []
            for o in orders:
                items_payload = []
                for i in o.items.all():
                    items_payload.append(
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
                    )

                data.append(
                    {
                        "id": o.id,
                        "status": o.status,
                        "dt": o.dt.isoformat(),
                        "items": items_payload,
                    }
                )

        return ok({"orders": data}, status.HTTP_200_OK)