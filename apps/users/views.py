
# Create your views here.

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import RegisterSerializer

from rest_framework.permissions import IsAuthenticated
from apps.users.permissions import IsClient
from .models import Contact
from .serializers import ContactSerializer

def ok(data=None, http_status=status.HTTP_200_OK):
    return Response({"Status": True, "data": data, "errors": None}, status=http_status)


def fail(errors, http_status=status.HTTP_400_BAD_REQUEST):
    return Response({"Status": False, "data": None, "errors": errors}, status=http_status)

class RegisterAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"Status": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()
        return Response({"Status": True, "data": {"id": user.id, "username": user.username, "email": user.email}, "errors": None},
                        status=status.HTTP_201_CREATED)


class ContactListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated, IsClient]

    def get(self, request, *args, **kwargs):
        qs = Contact.objects.filter(user=request.user).order_by("-created_at")
        return ok({"contacts": ContactSerializer(qs, many=True).data})

    def post(self, request, *args, **kwargs):
        serializer = ContactSerializer(data=request.data)
        if not serializer.is_valid():
            return fail(serializer.errors, status.HTTP_400_BAD_REQUEST)

        contact = serializer.save(user=request.user)
        return ok({"contact": ContactSerializer(contact).data}, status.HTTP_201_CREATED)


class ContactDetailAPIView(APIView):
    permission_classes = [IsAuthenticated, IsClient]

    def patch(self, request, contact_id: int, *args, **kwargs):
        contact = Contact.objects.filter(id=contact_id, user=request.user).first()
        if not contact:
            return fail("Contact not found", status.HTTP_404_NOT_FOUND)

        serializer = ContactSerializer(contact, data=request.data, partial=True)
        if not serializer.is_valid():
            return fail(serializer.errors, status.HTTP_400_BAD_REQUEST)

        serializer.save()
        return ok({"contact": serializer.data})

    def delete(self, request, contact_id: int, *args, **kwargs):
        contact = Contact.objects.filter(id=contact_id, user=request.user).first()
        if not contact:
            return fail("Contact not found", status.HTTP_404_NOT_FOUND)

        contact.delete()
        return ok({"deleted": True})