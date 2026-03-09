from __future__ import annotations

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema

from social_django.utils import load_backend, load_strategy
from social_core.exceptions import AuthException


# Явно ограничиваем backends, чтобы не открыть лишние провайдеры случайно
ALLOWED_BACKENDS = {"github", "google-oauth2"}


def _build_redirect_uri(django_request, backend: str) -> str:
    """
    Redirect URI ДОЛЖЕН совпадать с тем, что внесено в настройках провайдера.
    """
    return django_request.build_absolute_uri(
        reverse("social-api-complete", kwargs={"backend": backend})
    )


def _get_backend(django_request, backend: str, redirect_uri: str):
    """
    Получаем backend python-social-auth (social-core) через strategy.
    ВАЖНО: используем именно Django HttpRequest (request._request).
    """
    strategy = load_strategy(django_request)
    return load_backend(strategy=strategy, name=backend, redirect_uri=redirect_uri)


class SocialApiLoginAPIView(APIView):
    """
    API-first login:
    GET /api/auth/social/api/login/<backend>/

    Возвращает JSON:
    {
      "authorization_url": "...",
      "redirect_uri": "..."
    }
    """
    permission_classes = [AllowAny]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="backend",
                type=str,
                location=OpenApiParameter.PATH,
                description="Provider backend: github | google-oauth2",
                required=True,
            )
        ],
        responses={200: dict, 404: dict},
        examples=[
            OpenApiExample(
                "OK",
                value={
                    "authorization_url": "https://github.com/login/oauth/authorize?...",
                    "redirect_uri": "http://127.0.0.1:8000/api/auth/social/api/complete/github/",
                },
                response_only=True,
            )
        ],
    )
    def get(self, request, backend: str, *args, **kwargs):
        if backend not in ALLOWED_BACKENDS:
            return Response(
                {"detail": "Unsupported backend"},
                status=status.HTTP_404_NOT_FOUND,
            )

        django_request = request._request
        redirect_uri = _build_redirect_uri(django_request, backend)
        b = _get_backend(django_request, backend, redirect_uri)

        # auth_url() внутри создаёт state и кладёт его в session
        authorization_url = b.auth_url()

        return Response(
            {
                "authorization_url": authorization_url,
                "redirect_uri": redirect_uri,
            },
            status=status.HTTP_200_OK,
        )


class SocialApiCompleteAPIView(APIView):
    """
    API-first complete:
    GET /api/auth/social/api/complete/<backend>/?code=...&state=...

    Возвращает JWT:
    {
      "access": "...",
      "refresh": "...",
      "user": { "id": 1, "username": "...", "email": "..." }
    }
    """
    permission_classes = [AllowAny]

    @extend_schema(
        parameters=[
            OpenApiParameter(name="code", type=str, required=True),
            OpenApiParameter(name="state", type=str, required=True),
        ],
        responses={200: dict, 400: dict, 404: dict},
        examples=[
            OpenApiExample(
                "OK",
                value={
                    "access": "eyJ...",
                    "refresh": "eyJ...",
                    "user": {"id": 4, "username": "supplier1", "email": "mail@example.com"},
                },
                response_only=True,
            )
        ],
    )
    def get(self, request, backend: str, *args, **kwargs):
        if backend not in ALLOWED_BACKENDS:
            return Response(
                {"detail": "Unsupported backend"},
                status=status.HTTP_404_NOT_FOUND,
            )

        django_request = request._request
        redirect_uri = _build_redirect_uri(django_request, backend)
        b = _get_backend(django_request, backend, redirect_uri)

        try:
            # backend.complete() сам читает code/state из request (query params),
            # валидирует state через session и запускает pipeline.
            user = b.complete(user=None, redirect_name="next")
        except AuthException as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        User = get_user_model()
        if not isinstance(user, User):
            # На случай нестандартного возврата (редирект/ошибка)
            return Response(
                {"detail": "Authentication failed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {"id": user.id, "username": user.get_username(), "email": user.email},
            },
            status=status.HTTP_200_OK,
        )