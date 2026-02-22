
# Create your views here.
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.models import UserProfile
from .services.importer import import_price_from_url

from apps.catalog.models import Shop

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