# apps/partners/views.py

from django.db import transaction
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Shop
from apps.users.models import UserProfile
from .serializers import (
    PartnerUpdateSerializer,
    PartnerStateSerializer,
    PartnerShopCreateSerializer,
    PartnerShopPatchSerializer,
    UnifiedResponseSerializer,
)
from .services.importer import import_price_from_url


def ok(data=None, http_status=status.HTTP_200_OK):
    return Response({"Status": True, "data": data, "errors": None}, status=http_status)


def fail(errors, http_status=status.HTTP_400_BAD_REQUEST):
    return Response({"Status": False, "data": None, "errors": errors}, status=http_status)


class PartnerUpdateAPIView(APIView):
    """
    POST /api/partner/update/
    body: {"url": "https://.../price.yaml"}
    """

    @extend_schema(
        request=PartnerUpdateSerializer,
        responses={
            200: OpenApiResponse(response=UnifiedResponseSerializer, description="Import completed"),
            400: OpenApiResponse(response=UnifiedResponseSerializer, description="Validation/import error"),
            403: OpenApiResponse(response=UnifiedResponseSerializer, description="Forbidden"),
        },
        examples=[
            OpenApiExample(
                "Request example",
                value={"url": "https://raw.githubusercontent.com/netology-code/python-final-diplom/master/data/shop1.yaml"},
                request_only=True,
            ),
            OpenApiExample(
                "Success response (unified)",
                value={"Status": True, "data": {"imported": True}, "errors": None},
                response_only=True,
            ),
        ],
    )
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return fail("Log in required", status.HTTP_403_FORBIDDEN)

        role = getattr(getattr(request.user, "profile", None), "role", None)
        if role != UserProfile.Role.SUPPLIER:
            return fail("Only for suppliers", status.HTTP_403_FORBIDDEN)

        serializer = PartnerUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return fail(serializer.errors, status.HTTP_400_BAD_REQUEST)

        url = serializer.validated_data["url"]

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

    @extend_schema(
        request=PartnerStateSerializer,
        responses={
            200: OpenApiResponse(response=UnifiedResponseSerializer, description="State updated"),
            400: OpenApiResponse(response=UnifiedResponseSerializer, description="Validation error / no shop"),
            403: OpenApiResponse(response=UnifiedResponseSerializer, description="Forbidden"),
        },
        examples=[
            OpenApiExample("Disable", value={"state": False}, request_only=True),
            OpenApiExample("Enable", value={"state": True}, request_only=True),
            OpenApiExample(
                "Success response (unified)",
                value={"Status": True, "data": {"shop": "Связной", "state": False}, "errors": None},
                response_only=True,
            ),
        ],
    )
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return fail("Log in required", status.HTTP_403_FORBIDDEN)

        role = getattr(getattr(request.user, "profile", None), "role", None)
        if role != UserProfile.Role.SUPPLIER:
            return fail("Only for suppliers", status.HTTP_403_FORBIDDEN)

        serializer = PartnerStateSerializer(data=request.data)
        if not serializer.is_valid():
            return fail(serializer.errors, status.HTTP_400_BAD_REQUEST)

        state = serializer.validated_data["state"]

        shop = Shop.objects.filter(user=request.user).first()
        if not shop:
            return fail("No shop bound to this supplier yet", status.HTTP_400_BAD_REQUEST)

        shop.state = state
        shop.save(update_fields=["state"])

        return ok({"shop": shop.name, "state": shop.state}, status.HTTP_200_OK)


class PartnerShopAPIView(APIView):
    """
    POST  /api/partner/shop/   -> create/bind (only if no shop yet)
    GET   /api/partner/shop/   -> get bound shop
    PATCH /api/partner/shop/   -> update bound shop (name/url)
    """

    def _check_supplier(self, request):
        if not request.user.is_authenticated:
            return fail("Log in required", status.HTTP_403_FORBIDDEN)

        role = getattr(getattr(request.user, "profile", None), "role", None)
        if role != UserProfile.Role.SUPPLIER:
            return fail("Only for suppliers", status.HTTP_403_FORBIDDEN)

        return None

    @extend_schema(
        responses={
            200: OpenApiResponse(response=UnifiedResponseSerializer, description="Bound shop info"),
            403: OpenApiResponse(response=UnifiedResponseSerializer, description="Forbidden"),
            404: OpenApiResponse(response=UnifiedResponseSerializer, description="No shop bound"),
        },
        examples=[
            OpenApiExample(
                "Success response (unified)",
                value={
                    "Status": True,
                    "data": {"shop": "Связной", "url": "https://example.com", "state": True},
                    "errors": None,
                },
                response_only=True,
            ),
        ],
    )
    def get(self, request, *args, **kwargs):
        denied = self._check_supplier(request)
        if denied:
            return denied

        shop = Shop.objects.filter(user=request.user).first()
        if not shop:
            return fail("No shop bound to this supplier yet", status.HTTP_404_NOT_FOUND)

        return ok({"shop": shop.name, "url": shop.url, "state": shop.state}, status.HTTP_200_OK)

    @extend_schema(
        request=PartnerShopCreateSerializer,
        responses={
            201: OpenApiResponse(response=UnifiedResponseSerializer, description="Created new shop"),
            200: OpenApiResponse(response=UnifiedResponseSerializer, description="Bound existing free shop"),
            400: OpenApiResponse(response=UnifiedResponseSerializer, description="Validation error"),
            403: OpenApiResponse(response=UnifiedResponseSerializer, description="Forbidden"),
            409: OpenApiResponse(response=UnifiedResponseSerializer, description="Already bound / name conflict"),
        },
        examples=[
            OpenApiExample(
                "Create shop",
                value={"name": "Supplier1 Shop", "url": "https://supplier1.example"},
                request_only=True,
            ),
            OpenApiExample(
                "Conflict response (unified)",
                value={
                    "Status": False,
                    "data": None,
                    "errors": {"message": "Shop already bound to this supplier", "shop": "Связной"},
                },
                response_only=True,
            ),
        ],
    )
    def post(self, request, *args, **kwargs):
        denied = self._check_supplier(request)
        if denied:
            return denied

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
                # Если магазин закреплён за другим поставщиком — конфликт
                if shop.user_id and shop.user_id != request.user.id:
                    return fail("Shop name is already used by another supplier", status.HTTP_409_CONFLICT)

                # shop.user is None -> привязываем
                shop.user = request.user
                if url:
                    shop.url = url
                    shop.save(update_fields=["user", "url"])
                else:
                    shop.save(update_fields=["user"])

                return ok({"shop": shop.name, "url": shop.url, "state": shop.state}, status.HTTP_200_OK)

            # Создаём новый shop и привязываем к поставщику
            shop = Shop.objects.create(name=name, url=url, user=request.user, state=True)

        return ok({"shop": shop.name, "url": shop.url, "state": shop.state}, status.HTTP_201_CREATED)

    @extend_schema(
        request=PartnerShopPatchSerializer,
        responses={
            200: OpenApiResponse(response=UnifiedResponseSerializer, description="Updated"),
            400: OpenApiResponse(response=UnifiedResponseSerializer, description="Validation error"),
            403: OpenApiResponse(response=UnifiedResponseSerializer, description="Forbidden"),
            404: OpenApiResponse(response=UnifiedResponseSerializer, description="No shop bound"),
            409: OpenApiResponse(response=UnifiedResponseSerializer, description="Name conflict"),
        },
        examples=[
            OpenApiExample("Patch url", value={"url": "https://supplier1.example"}, request_only=True),
            OpenApiExample("Patch name", value={"name": "Supplier1 Shop"}, request_only=True),
            OpenApiExample(
                "Success response (unified)",
                value={
                    "Status": True,
                    "data": {"shop": "Связной", "url": "https://supplier1.example", "state": True},
                    "errors": None,
                },
                response_only=True,
            ),
        ],
    )
    def patch(self, request, *args, **kwargs):
        denied = self._check_supplier(request)
        if denied:
            return denied

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