# import → basket → checkout → emails → partner orders

import logging
import pytest

logger = logging.getLogger(__name__)


@pytest.mark.django_db
def test_register_and_login_jwt(api_client):
    logger.info("Register user via /api/auth/register/")
    r = api_client.post(
        "/api/auth/register/",
        {"username": "reg_user", "email": "reg_user@test.local", "password": "pass12345"},
        format="json",
    )
    assert r.status_code == 201, r.data
    assert r.data["Status"] is True

    logger.info("Login via /api/auth/login/")
    r = api_client.post(
        "/api/auth/login/",
        {"username": "reg_user", "password": "pass12345"},
        format="json",
    )
    assert r.status_code == 200, r.data
    assert "access" in r.data and "refresh" in r.data