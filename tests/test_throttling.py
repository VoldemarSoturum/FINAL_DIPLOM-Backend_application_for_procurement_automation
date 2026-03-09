import pytest
from django.core.cache import cache
from django.test import override_settings

@pytest.mark.django_db
@override_settings(REST_FRAMEWORK={
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.BasicAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "2/min",
    },
})
def test_throttling_anon_rate_limit(api_client):
    cache.clear()

    r1 = api_client.get("/api/catalog/categories/")
    r2 = api_client.get("/api/catalog/categories/")
    r3 = api_client.get("/api/catalog/categories/")  # 3-й должен превысить 2/min

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 429