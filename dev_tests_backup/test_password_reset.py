import logging
import pytest
from django.core import mail

logger = logging.getLogger(__name__)


@pytest.mark.django_db
def test_password_reset_flow(api_client, user_model):
    user_model.objects.create_user(username="u1", email="u1@test.local", password="oldpass123")

    logger.info("Request password reset")
    mail.outbox.clear()
    r = api_client.post("/api/password_reset/", {"email": "u1@test.local"}, format="json")
    assert r.status_code in (200, 201), r.data
    assert len(mail.outbox) == 1

    body = mail.outbox[0].body
    token_line = [line for line in body.splitlines() if "Your reset token:" in line]
    assert token_line, body
    token = token_line[0].split("Your reset token:")[1].strip()
    assert token

    logger.info("Confirm password reset")
    r = api_client.post("/api/password_reset/confirm/", {"token": token, "password": "NEWpass12345"}, format="json")
    assert r.status_code in (200, 201), r.data

    logger.info("Login with new password")
    r = api_client.post("/api/auth/login/", {"username": "u1", "password": "NEWpass12345"}, format="json")
    assert r.status_code == 200, r.data
    assert "access" in r.data