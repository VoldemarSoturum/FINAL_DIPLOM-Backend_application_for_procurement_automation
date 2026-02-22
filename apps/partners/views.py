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
    ShopResponseSerializer,
)
from .services.importer import import_price_from_url


class PartnerUpdateAPIView(APIView):
    """
    POST /api/partner/update/
    body: {"url": "https://.../price.yaml"}
    """

    @extend_schema(
        request=PartnerUpdateSerializer,
        responses={
            200: OpenApiResponse(response=ShopResponseSerializer, description="Import completed"),
            400: OpenApiResponse(response=ShopResponseSerializer, description="Validation/import error"),
            403: OpenApiResponse(response=ShopResponseSerializer, description="Forbidden"),
        },
        examples=[
            OpenApiExample(
                "Request example",
                value={"url": "https://raw.githubusercontent.com/netology-code/python-final-diplom/master/data/shop1.yaml"},
                request_only=True,
            ),
            OpenApiExample(
                "Success response",
                value={"Status": True},
                response_only=True,
            ),
        ],
    )
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"Status": False, "Error": "Log in required"}, status=status.HTTP_403_FORBIDDEN)

        role = getattr(getattr(request.user, "profile", None), "role", None)
        if role != UserProfile.Role.SUPPLIER:
            return Response({"Status": False, "Error": "Only for suppliers"}, status=status.HTTP_403_FORBIDDEN)

        serializer = PartnerUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"Status": False, "Errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        url = serializer.validated_data["url"]

        result = import_price_from_url(user=request.user, url=url)
        if not result.get("Status", False):
            return Response(result, status=result.get("http_status", status.HTTP_400_BAD_REQUEST))

        return Response(result, status=status.HTTP_200_OK)


class PartnerStateAPIView(APIView):
    """
    POST /api/partner/state/
    body: {"state": true/false}
    """

    @extend_schema(
        request=PartnerStateSerializer,
        responses={
            200: OpenApiResponse(response=ShopResponseSerializer, description="State updated"),
            400: OpenApiResponse(response=ShopResponseSerializer, description="Validation error / no shop"),
            403: OpenApiResponse(response=ShopResponseSerializer, description="Forbidden"),
        },
        examples=[
            OpenApiExample("Disable", value={"state": False}, request_only=True),
            OpenApiExample("Enable", value={"state": True}, request_only=True),
            OpenApiExample(
                "Success response",
                value={"Status": True, "shop": "Связной", "state": False},
                response_only=True,
            ),
        ],
    )
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"Status": False, "Error": "Log in required"}, status=status.HTTP_403_FORBIDDEN)

        role = getattr(getattr(request.user, "profile", None), "role", None)
        if role != UserProfile.Role.SUPPLIER:
            return Response({"Status": False, "Error": "Only for suppliers"}, status=status.HTTP_403_FORBIDDEN)

        serializer = PartnerStateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"Status": False, "Errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        state = serializer.validated_data["state"]

        shop = Shop.objects.filter(user=request.user).first()
        if not shop:
            return Response(
                {"Status": False, "Error": "No shop bound to this supplier yet"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        shop.state = state
        shop.save(update_fields=["state"])

        return Response({"Status": True, "shop": shop.name, "state": shop.state}, status=status.HTTP_200_OK)


class PartnerShopAPIView(APIView):
    """
    POST  /api/partner/shop/   -> create/bind (only if no shop yet)
    GET   /api/partner/shop/   -> get bound shop
    PATCH /api/partner/shop/   -> update bound shop (name/url)
    """

    def _check_supplier(self, request):
        if not request.user.is_authenticated:
            return Response({"Status": False, "Error": "Log in required"}, status=status.HTTP_403_FORBIDDEN)

        role = getattr(getattr(request.user, "profile", None), "role", None)
        if role != UserProfile.Role.SUPPLIER:
            return Response({"Status": False, "Error": "Only for suppliers"}, status=status.HTTP_403_FORBIDDEN)

        return None

    @extend_schema(
        responses={
            200: OpenApiResponse(response=ShopResponseSerializer, description="Bound shop info"),
            403: OpenApiResponse(response=ShopResponseSerializer, description="Forbidden"),
            404: OpenApiResponse(response=ShopResponseSerializer, description="No shop bound"),
        },
        examples=[
            OpenApiExample(
                "Success response",
                value={"Status": True, "shop": "Связной", "url": "https://example.com", "state": True},
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
            return Response(
                {"Status": False, "Error": "No shop bound to this supplier yet"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {"Status": True, "shop": shop.name, "url": shop.url, "state": shop.state},
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        request=PartnerShopCreateSerializer,
        responses={
            201: OpenApiResponse(response=ShopResponseSerializer, description="Created new shop"),
            200: OpenApiResponse(response=ShopResponseSerializer, description="Bound existing free shop"),
            400: OpenApiResponse(response=ShopResponseSerializer, description="Validation error"),
            403: OpenApiResponse(response=ShopResponseSerializer, description="Forbidden"),
            409: OpenApiResponse(response=ShopResponseSerializer, description="Already bound / name conflict"),
        },
        examples=[
            OpenApiExample(
                "Create shop",
                value={"name": "Supplier1 Shop", "url": "https://supplier1.example"},
                request_only=True,
            ),
            OpenApiExample(
                "Conflict response",
                value={"Status": False, "Error": "Shop already bound to this supplier", "shop": "Связной"},
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
            return Response(
                {"Status": False, "Error": "Shop already bound to this supplier", "shop": existing.name},
                status=status.HTTP_409_CONFLICT,
            )

        serializer = PartnerShopCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"Status": False, "Errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        name = serializer.validated_data["name"].strip()
        url = serializer.validated_data.get("url", "")
        url = url.strip() if isinstance(url, str) else ""

        with transaction.atomic():
            shop = Shop.objects.filter(name=name).select_for_update().first()

            if shop:
                # Если магазин закреплён за другим поставщиком — конфликт
                if shop.user_id and shop.user_id != request.user.id:
                    return Response(
                        {"Status": False, "Error": "Shop name is already used by another supplier"},
                        status=status.HTTP_409_CONFLICT,
                    )

                # shop.user is None -> привязываем
                shop.user = request.user
                if url:
                    shop.url = url
                    shop.save(update_fields=["user", "url"])
                else:
                    shop.save(update_fields=["user"])

                return Response(
                    {"Status": True, "shop": shop.name, "url": shop.url, "state": shop.state},
                    status=status.HTTP_200_OK,
                )

            # Создаём новый shop и привязываем к поставщику
            shop = Shop.objects.create(name=name, url=url, user=request.user, state=True)

        return Response(
            {"Status": True, "shop": shop.name, "url": shop.url, "state": shop.state},
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        request=PartnerShopPatchSerializer,
        responses={
            200: OpenApiResponse(response=ShopResponseSerializer, description="Updated"),
            400: OpenApiResponse(response=ShopResponseSerializer, description="Validation error"),
            403: OpenApiResponse(response=ShopResponseSerializer, description="Forbidden"),
            404: OpenApiResponse(response=ShopResponseSerializer, description="No shop bound"),
            409: OpenApiResponse(response=ShopResponseSerializer, description="Name conflict"),
        },
        examples=[
            OpenApiExample("Patch url", value={"url": "https://supplier1.example"}, request_only=True),
            OpenApiExample("Patch name", value={"name": "Supplier1 Shop"}, request_only=True),
        ],
    )
    def patch(self, request, *args, **kwargs):
        denied = self._check_supplier(request)
        if denied:
            return denied

        shop = Shop.objects.filter(user=request.user).first()
        if not shop:
            return Response(
                {"Status": False, "Error": "No shop bound to this supplier yet"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = PartnerShopPatchSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"Status": False, "Errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        new_name = serializer.validated_data.get("name", None)
        new_url = serializer.validated_data.get("url", None)

        # Если меняем name — проверяем уникальность
        with transaction.atomic():
            if new_name is not None:
                new_name = str(new_name).strip()
                if not new_name:
                    return Response({"Status": False, "Error": "name cannot be empty"}, status=status.HTTP_400_BAD_REQUEST)

                if new_name != shop.name:
                    conflict = Shop.objects.select_for_update().filter(name=new_name).exclude(id=shop.id).first()
                    if conflict:
                        return Response(
                            {"Status": False, "Error": "Shop name is already used"},
                            status=status.HTTP_409_CONFLICT,
                        )
                    shop.name = new_name

            if new_url is not None:
                shop.url = str(new_url).strip()

            shop.save()

        return Response(
            {"Status": True, "shop": shop.name, "url": shop.url, "state": shop.state},
            status=status.HTTP_200_OK,
        )