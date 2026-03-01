# test for control and role

import pytest


@pytest.mark.django_db
def test_client_cannot_access_partner_endpoints(client_api):
    r = client_api.get("/api/partner/orders/")
    assert r.status_code == 403


@pytest.mark.django_db
def test_supplier_cannot_access_basket(supplier_api):
    r = supplier_api.get("/api/basket/")
    assert r.status_code == 403