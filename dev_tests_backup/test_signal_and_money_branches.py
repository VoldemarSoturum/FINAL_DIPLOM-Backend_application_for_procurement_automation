import pytest
from decimal import Decimal
from django.core import mail
from django.contrib.auth import get_user_model

from apps.orders.services import emails as email_mod
from apps.users.password_reset_signals import password_reset_token_created


@pytest.mark.django_db
def test_money_helper_branches():
    # закрываем missing lines 13,16 в emails.py
    assert email_mod._money(None) == "-"
    assert email_mod._money(Decimal("1.234")) == "1.23"
    assert email_mod._money("x") == "x"


@pytest.mark.django_db
def test_password_reset_signal_early_return_no_email():
    User = get_user_model()
    u = User.objects.create_user(username="sig_no_email", password="pass12345", email="")

    class DummyToken:
        user = u
        key = "DUMMY"

    mail.outbox.clear()
    password_reset_token_created(sender=None, instance=None, reset_password_token=DummyToken())
    assert len(mail.outbox) == 0