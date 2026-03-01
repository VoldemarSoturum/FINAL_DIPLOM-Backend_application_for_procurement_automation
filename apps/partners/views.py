# apps/partners/views.py

from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils.dateparse import parse_date
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Shop
from apps.orders.models import Order, OrderItem
from apps.users.models import UserProfile
from apps.users.permissions import IsSupplier

from .serializers import (
    PartnerUpdateSerializer,
    PartnerStateSerializer,
    PartnerShopCreateSerializer,
    PartnerShopPatchSerializer,
    UnifiedResponseSerializer,
)
from .services.importer import import_price_from_url  # <-- важно: чтобы monkeypatch в тестах работал
from .tasks import import_price_task  # <-- async режим


def ok(data=None, http_status=status.HTTP_200_OK):
    return Response({"Status": True, "data": data, "errors": None}, status=http_status)


def fail(errors, http_status=status.HTTP_400_BAD_REQUEST):
    return Response({"Status": False, "data": None, "errors": errors}, status=http_status)


def check_supplier(request):
    if not request.user.is_authenticated:
        return fail("Log in required", status.HTTP_403_FORBIDDEN)

    role = getattr(getattr(request.user, "profile", None), "role", None)
    if role != UserProfile.Role.SUPPLIER:
        return fail("Only for suppliers", status.HTTP_403_FORBIDDEN)

    return None


# class PartnerUpdateAPIView(APIView):
#     """
#     POST /api/partner/update/
#     body: {"url": "https://.../price.yaml"}
#     """
#     permission_classes = [IsAuthenticated, IsSupplier]
#
#     @extend_schema(
#         request=PartnerUpdateSerializer,
#         responses={
#             200: OpenApiResponse(response=UnifiedResponseSerializer, description="Import completed (eager/tests)"),
#             202: OpenApiResponse(response=UnifiedResponseSerializer, description="Import queued (async)"),
#             400: OpenApiResponse(response=UnifiedResponseSerializer, description="Validation/import error"),
#             403: OpenApiResponse(response=UnifiedResponseSerializer, description="Forbidden"),
#         },
#         examples=[
#             OpenApiExample(
#                 "Request example",
#                 value={"url": "https://raw.githubusercontent.com/netology-code/python-final-diplom/master/data/shop1.yaml"},
#                 request_only=True,
#             ),
#             OpenApiExample(
#                 "Sync success (eager/tests)",
#                 value={"Status": True, "data": {"imported": True}, "errors": None},
#                 response_only=True,
#             ),
#             OpenApiExample(
#                 "Async queued (prod)",
#                 value={"Status": True, "data": {"queued": True, "task_id": "..."}, "errors": None},
#                 response_only=True,
#             ),
#         ],
#     )
#     def post(self, request, *args, **kwargs):
#         serializer = PartnerUpdateSerializer(data=request.data)
#         if not serializer.is_valid():
#             return fail(serializer.errors, status.HTTP_400_BAD_REQUEST)
#
#         url = serializer.validated_data["url"]
#
#         # tests/eager: синхронно -> чтобы monkeypatch на import_price_from_url работал
#         if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
#             result = import_price_from_url(user=request.user, url=url)
#             if not result.get("Status", False):
#                 err = result.get("Error") or result.get("Errors") or "Import failed"
#                 return fail(err, result.get("http_status", status.HTTP_400_BAD_REQUEST))
#             return ok({"imported": True}, status.HTTP_200_OK)
#
#         # prod: очередь celery
#         async_result = import_price_task.delay(request.user.id, url)
#         return ok({"queued": True, "task_id": async_result.id}, status.HTTP_202_ACCEPTED)
class PartnerUpdateAPIView(APIView):
    """
    POST /api/partner/update/
    body: {"url": "https://.../price.yaml"}
    """
    permission_classes = [IsAuthenticated, IsSupplier]

    @extend_schema(
        request=PartnerUpdateSerializer,
        responses={
            200: OpenApiResponse(response=UnifiedResponseSerializer, description="Import completed (sync/eager)"),
            202: OpenApiResponse(response=UnifiedResponseSerializer, description="Import accepted (async)"),
            400: OpenApiResponse(response=UnifiedResponseSerializer, description="Validation/import error"),
            403: OpenApiResponse(response=UnifiedResponseSerializer, description="Forbidden"),
        },
        examples=[
            OpenApiExample(
                "Request example",
                value={
                    "url": "https://raw.githubusercontent.com/netology-code/python-final-diplom/master/data/shop1.yaml"},
                request_only=True,
            ),
            OpenApiExample(
                "Sync success",
                value={"Status": True, "data": {"imported": True}, "errors": None},
                response_only=True,
            ),
            OpenApiExample(
                "Async accepted",
                value={"Status": True, "data": {"task_id": "a1b2c3"}, "errors": None},
                response_only=True,
            ),
        ],
    )
    def post(self, request, *args, **kwargs):
        serializer = PartnerUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return fail(serializer.errors, status.HTTP_400_BAD_REQUEST)

        url = serializer.validated_data["url"]

        # ASYNC branch (real celery enqueue)
        if not getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
            async_result = import_price_task.delay(user_id=request.user.id, url=url)
            return ok({"task_id": async_result.id}, status.HTTP_202_ACCEPTED)

        # SYNC branch (tests / eager)
        result = import_price_from_url(user=request.user, url=url)
        if not result.get("Status", False):
            err = result.get("Error") or result.get("Errors") or "Import failed"
            return fail(err, result.get("http_status", status.HTTP_400_BAD_REQUEST))

        return ok({"imported": True}, status.HTTP_200_OK)

class PartnerStateAPIView(APIView):
    """
    POST /api/partner/state/
    body: {"state": true/false}
    """
    permission_classes = [IsAuthenticated, IsSupplier]

    @extend_schema(
        request=PartnerStateSerializer,
        responses={
            200: OpenApiResponse(response=UnifiedResponseSerializer, description="State updated"),
            400: OpenApiResponse(response=UnifiedResponseSerializer, description="Validation error / no shop"),
            403: OpenApiResponse(response=UnifiedResponseSerializer, description="Forbidden"),
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = PartnerStateSerializer(data=request.data)
        if not serializer.is_valid():
            return fail(serializer.errors, status.HTTP_400_BAD_REQUEST)

        state_value = serializer.validated_data["state"]

        shop = Shop.objects.filter(user=request.user).first()
        if not shop:
            return fail("No shop bound to this supplier yet", status.HTTP_400_BAD_REQUEST)

        shop.state = state_value
        shop.save(update_fields=["state"])

        return ok({"shop": shop.name, "state": shop.state}, status.HTTP_200_OK)


class PartnerShopAPIView(APIView):
    """
    POST  /api/partner/shop/   -> create/bind (only if no shop yet)
    GET   /api/partner/shop/   -> get bound shop
    PATCH /api/partner/shop/   -> update bound shop (name/url)
    """
    permission_classes = [IsAuthenticated, IsSupplier]

    def get(self, request, *args, **kwargs):
        shop = Shop.objects.filter(user=request.user).first()
        if not shop:
            return fail("No shop bound to this supplier yet", status.HTTP_404_NOT_FOUND)

        return ok({"shop": shop.name, "url": shop.url, "state": shop.state}, status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        existing = Shop.objects.filter(user=request.user).first()
        if existing:
            return fail(
                {"message": "Shop already bound to this supplier", "shop": existing.name},
                status.HTTP_409_CONFLICT,
            )

        serializer = PartnerShopCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return fail(serializer.errors, status.HTTP_400_BAD_REQUEST)

        name = serializer.validated_data["name"].strip()
        url = serializer.validated_data.get("url", "")
        url = url.strip() if isinstance(url, str) else ""

        with transaction.atomic():
            shop = Shop.objects.filter(name=name).select_for_update().first()

            if shop:
                if shop.user_id and shop.user_id != request.user.id:
                    return fail("Shop name is already used by another supplier", status.HTTP_409_CONFLICT)

                shop.user = request.user
                if url:
                    shop.url = url
                    shop.save(update_fields=["user", "url"])
                else:
                    shop.save(update_fields=["user"])

                return ok({"shop": shop.name, "url": shop.url, "state": shop.state}, status.HTTP_200_OK)

            shop = Shop.objects.create(name=name, url=url, user=request.user, state=True)

        return ok({"shop": shop.name, "url": shop.url, "state": shop.state}, status.HTTP_201_CREATED)

    def patch(self, request, *args, **kwargs):
        shop = Shop.objects.filter(user=request.user).first()
        if not shop:
            return fail("No shop bound to this supplier yet", status.HTTP_404_NOT_FOUND)

        serializer = PartnerShopPatchSerializer(data=request.data)
        if not serializer.is_valid():
            return fail(serializer.errors, status.HTTP_400_BAD_REQUEST)

        new_name = serializer.validated_data.get("name", None)
        new_url = serializer.validated_data.get("url", None)

        with transaction.atomic():
            if new_name is not None:
                new_name = str(new_name).strip()
                if not new_name:
                    return fail("name cannot be empty", status.HTTP_400_BAD_REQUEST)

                if new_name != shop.name:
                    conflict = (
                        Shop.objects.select_for_update()
                        .filter(name=new_name)
                        .exclude(id=shop.id)
                        .first()
                    )
                    if conflict:
                        return fail("Shop name is already used", status.HTTP_409_CONFLICT)
                    shop.name = new_name

            if new_url is not None:
                shop.url = str(new_url).strip()

            shop.save()

        return ok({"shop": shop.name, "url": shop.url, "state": shop.state}, status.HTTP_200_OK)


class PartnerOrdersAPIView(APIView):
    """
    GET /api/partner/orders/
    Supplier sees only orders containing items from his shop.
    """
    permission_classes = [IsAuthenticated, IsSupplier]

    def get(self, request, *args, **kwargs):
        shop = Shop.objects.filter(user=request.user).first()
        if not shop:
            return fail("No shop bound to this supplier yet", status.HTTP_400_BAD_REQUEST)

        qs = (
            OrderItem.objects.select_related("order", "order__user", "product")
            .filter(shop=shop)
            .exclude(order__status=Order.Status.BASKET)
        )

        status_param = request.query_params.get("status")
        if status_param:
            qs = qs.filter(order__status=status_param)

        date_from = request.query_params.get("date_from")
        if date_from:
            df = parse_date(date_from)
            if not df:
                return fail("date_from must be YYYY-MM-DD", status.HTTP_400_BAD_REQUEST)
            qs = qs.filter(order__dt__date__gte=df)

        date_to = request.query_params.get("date_to")
        if date_to:
            dt_ = parse_date(date_to)
            if not dt_:
                return fail("date_to must be YYYY-MM-DD", status.HTTP_400_BAD_REQUEST)
            qs = qs.filter(order__dt__date__lte=dt_)

        orders_map = {}
        for item in qs.order_by("-order__dt", "order_id", "id"):
            order = item.order
            key = order.id

            if key not in orders_map:
                orders_map[key] = {
                    "id": order.id,
                    "dt": order.dt.isoformat(),
                    "status": order.status,
                    "customer": {
                        "id": order.user_id,
                        "username": getattr(order.user, "username", ""),
                        "email": getattr(order.user, "email", ""),
                    },
                    "items": [],
                }

            unit_price = item.unit_price
            total = None
            if unit_price is not None:
                total = (unit_price * Decimal(item.quantity)).quantize(Decimal("0.01"))

            orders_map[key]["items"].append(
                {
                    "id": item.id,
                    "product_id": item.product_id,
                    "product_name": item.product.name,
                    "quantity": item.quantity,
                    "unit_price": str(item.unit_price) if item.unit_price is not None else None,
                    "unit_price_rrc": str(item.unit_price_rrc) if item.unit_price_rrc is not None else None,
                    "total": str(total) if total is not None else None,
                }
            )

        return ok({"orders": list(orders_map.values())}, status.HTTP_200_OK)