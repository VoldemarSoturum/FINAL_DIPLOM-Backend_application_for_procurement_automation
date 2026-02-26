
# Create your views here.

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import RegisterSerializer


class RegisterAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"Status": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()
        return Response({"Status": True, "data": {"id": user.id, "username": user.username, "email": user.email}, "errors": None},
                        status=status.HTTP_201_CREATED)