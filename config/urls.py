"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Class-based views
    1. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# from django.contrib import admin
from baton.autodiscover import admin
from django.urls import path, include

from rest_framework.decorators import api_view
from rest_framework.response import Response

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)


@api_view(["GET"])
def health(request):
    return Response({"status": "ok"})


urlpatterns = [
    path("", health),

    path("baton/", include("baton.urls")),

    path("admin/", admin.site.urls),

    # Password reset endpoints
    path("api/password_reset/", include("django_rest_passwordreset.urls", namespace="password_reset")),

    # OpenAPI schema + docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),

    path("api/", include("apps.users.urls")),

    path("api/partner/", include("apps.partners.urls")),

    path("api/catalog/", include("apps.catalog.urls")),

    path("api/", include("apps.orders.urls")),

    path("api/auth/social/", include("social_django.urls", namespace="social")),
]