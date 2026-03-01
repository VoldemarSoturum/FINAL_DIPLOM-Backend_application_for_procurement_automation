from rest_framework.permissions import BasePermission

from apps.users.models import UserProfile


def _get_role(user):
    # ВАЖНО: не использовать user.profile (может быть stale cache).
    return (
        UserProfile.objects.filter(user=user)
        .values_list("role", flat=True)
        .first()
    )


class IsSupplier(BasePermission):
    message = "Only suppliers can access this endpoint."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and _get_role(request.user) == UserProfile.Role.SUPPLIER
        )


class IsClient(BasePermission):
    message = "Only clients can access this endpoint."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and _get_role(request.user) == UserProfile.Role.CLIENT
        )