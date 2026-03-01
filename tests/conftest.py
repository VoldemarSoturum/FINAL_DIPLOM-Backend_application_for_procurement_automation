import logging

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from tqdm import tqdm

from apps.users.models import UserProfile

logger = logging.getLogger(__name__)

_PROGRESS = None


def pytest_collection_modifyitems(session, config, items):
    global _PROGRESS
    _PROGRESS = tqdm(total=len(items), desc="Tests", unit="test", dynamic_ncols=True)


def pytest_runtest_logreport(report):
    global _PROGRESS
    if _PROGRESS is None:
        return
    if report.when == "call":
        _PROGRESS.update(1)
        _PROGRESS.set_postfix_str(report.outcome)


def pytest_sessionfinish(session, exitstatus):
    global _PROGRESS
    if _PROGRESS is not None:
        _PROGRESS.close()
        _PROGRESS = None


@pytest.fixture()
def api_client():
    return APIClient()


@pytest.fixture()
def user_model():
    return get_user_model()


@pytest.fixture()
def supplier_user(db, user_model):
    user = user_model.objects.create_user(
        username="supplier_test",
        password="supplier_pass",
        email="supplier@test.local",
    )
    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.role = UserProfile.Role.SUPPLIER
    profile.save(update_fields=["role"])
    logger.info("Created supplier user id=%s", user.id)
    return user


@pytest.fixture()
def client_user(db, user_model):
    user = user_model.objects.create_user(
        username="client_test",
        password="client_pass",
        email="client@test.local",
    )
    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.role = UserProfile.Role.CLIENT
    profile.save(update_fields=["role"])
    logger.info("Created client user id=%s", user.id)
    return user


@pytest.fixture()
def supplier_api(supplier_user):
    c = APIClient()
    c.force_authenticate(user=supplier_user)
    return c


@pytest.fixture()
def client_api(client_user):
    c = APIClient()
    c.force_authenticate(user=client_user)
    return c
@pytest.fixture()
def client_access(api_client, db):
    """
    JWT headers for a client user.
    Returns (client, headers)
    """
    User = get_user_model()
    u = User.objects.create_user(
        username="client_access",
        password="client_pass",
        email="client_access@test.local",
    )
    profile, _ = UserProfile.objects.get_or_create(user=u)
    profile.role = UserProfile.Role.CLIENT
    profile.save(update_fields=["role"])

    r = api_client.post(
        "/api/auth/login/",
        {"username": "client_access", "password": "client_pass"},
        format="json",
    )
    assert r.status_code == 200, r.json()
    token = r.json()["access"]

    return api_client, {"HTTP_AUTHORIZATION": f"Bearer {token}"}