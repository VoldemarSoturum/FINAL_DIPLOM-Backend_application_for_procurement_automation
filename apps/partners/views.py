
# Create your views here.
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.models import UserProfile
from .services.importer import import_price_from_url

from apps.catalog.models import Shop
from django.db import transaction

class PartnerUpdateAPIView(APIView):
    """
    POST /api/partner/update/
    body: {"url": "https://.../price.yaml"}
    """

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"Status": False, "Error": "Log in required"}, status=status.HTTP_403_FORBIDDEN)

        # Проверка роли поставщика (у тебя роль хранится в профиле)
        role = getattr(getattr(request.user, "profile", None), "role", None)
        if role != UserProfile.Role.SUPPLIER:
            return Response({"Status": False, "Error": "Only for suppliers"}, status=status.HTTP_403_FORBIDDEN)

        url = request.data.get("url")
        if not url:
            return Response({"Status": False, "Error": "url is required"}, status=status.HTTP_400_BAD_REQUEST)

        validate_url = URLValidator()
        try:
            validate_url(url)
        except ValidationError as e:
            return Response({"Status": False, "Error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        result = import_price_from_url(user=request.user, url=url)
        if not result["Status"]:
            return Response(result, status=result.get("http_status", status.HTTP_400_BAD_REQUEST))

        return Response(result, status=status.HTTP_200_OK)

class PartnerStateAPIView(APIView):
    """
    POST /api/partner/state/
    body: {"state": true/false}
    """

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"Status": False, "Error": "Log in required"}, status=status.HTTP_403_FORBIDDEN)

        role = getattr(getattr(request.user, "profile", None), "role", None)
        if role != UserProfile.Role.SUPPLIER:
            return Response({"Status": False, "Error": "Only for suppliers"}, status=status.HTTP_403_FORBIDDEN)

        state = request.data.get("state")
        if not isinstance(state, bool):
            return Response(
                {"Status": False, "Error": "state must be boolean true/false"},
                status=status.HTTP_400_BAD_REQUEST,
            )

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
    POST /api/partner/shop/
    body: {"name": "...", "url": "..."}
    Create/bind shop to supplier (only if supplier has no shop yet).
    """
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

    def get(self, request, *args, **kwargs):
        denied = self._check_supplier(request)
        if denied:
            return denied

        shop = Shop.objects.filter(user=request.user).first()
        if not shop:
            return Response({"Status": False, "Error": "No shop bound to this supplier yet"},
                            status=status.HTTP_404_NOT_FOUND)

        return Response(
            {"Status": True, "shop": shop.name, "url": shop.url, "state": shop.state},
            status=status.HTTP_200_OK,
        )

    def patch(self, request, *args, **kwargs):
        denied = self._check_supplier(request)
        if denied:
            return denied

        shop = Shop.objects.filter(user=request.user).first()
        if not shop:
            return Response({"Status": False, "Error": "No shop bound to this supplier yet"},
                            status=status.HTTP_404_NOT_FOUND)

        new_name = request.data.get("name")
        new_url = request.data.get("url")

        if new_name is not None:
            new_name = str(new_name).strip()
            if not new_name:
                return Response({"Status": False, "Error": "name cannot be empty"}, status=status.HTTP_400_BAD_REQUEST)

        if new_url is not None:
            new_url = str(new_url).strip()

        # Если меняем name — нужно проверить уникальность
        with transaction.atomic():
            if new_name and new_name != shop.name:
                conflict = Shop.objects.select_for_update().filter(name=new_name).exclude(id=shop.id).first()
                if conflict:
                    return Response(
                        {"Status": False, "Error": "Shop name is already used"},
                        status=status.HTTP_409_CONFLICT,
                    )
                shop.name = new_name

            if new_url is not None:
                shop.url = new_url

            shop.save()

        return Response(
            {"Status": True, "shop": shop.name, "url": shop.url, "state": shop.state},
            status=status.HTTP_200_OK,
        )

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"Status": False, "Error": "Log in required"}, status=status.HTTP_403_FORBIDDEN)

        role = getattr(getattr(request.user, "profile", None), "role", None)
        if role != UserProfile.Role.SUPPLIER:
            return Response({"Status": False, "Error": "Only for suppliers"}, status=status.HTTP_403_FORBIDDEN)

        # Уже привязан магазин?
        existing = Shop.objects.filter(user=request.user).first()
        if existing:
            return Response(
                {"Status": False, "Error": "Shop already bound to this supplier", "shop": existing.name},
                status=status.HTTP_409_CONFLICT,
            )

        name = (request.data.get("name") or "").strip()
        url = (request.data.get("url") or "").strip()

        if not name:
            return Response({"Status": False, "Error": "name is required"}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            shop = Shop.objects.filter(name=name).select_for_update().first()

            if shop:
                # Если магазин уже закреплён за другим поставщиком — запрещаем
                if shop.user_id and shop.user_id != request.user.id:
                    return Response(
                        {"Status": False, "Error": "Shop name is already used by another supplier"},
                        status=status.HTTP_409_CONFLICT,
                    )

                # Иначе (shop.user is None) — привязываем
                shop.user = request.user
                if url:
                    shop.url = url
                shop.save(update_fields=["user", "url"] if url else ["user"])

                return Response(
                    {"Status": True, "shop": shop.name, "url": shop.url, "state": shop.state},
                    status=status.HTTP_200_OK,
                )

            # Создаём новый
            shop = Shop.objects.create(name=name, url=url, user=request.user, state=True)

        return Response(
            {"Status": True, "shop": shop.name, "url": shop.url, "state": shop.state},
            status=status.HTTP_201_CREATED,
        )