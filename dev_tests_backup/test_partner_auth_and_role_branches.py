import pytest
from django.utils import timezone

from apps.catalog.models import Shop, Category, Product
from apps.orders.models import Order, OrderItem


@pytest.mark.django_db
def test_partner_endpoints_require_login(api_client):
    # update -> unauthenticated обычно 401
    r = api_client.post("/api/partner/update/", {"url": "http://x"}, format="json")
    assert r.status_code in (401, 403), r.json()
    # может быть {"detail": "..."} или unified fail
    assert ("detail" in r.json()) or ("Status" in r.json())

    # state
    r = api_client.post("/api/partner/state/", {"state": True}, format="json")
    assert r.status_code in (401, 403), r.json()
    assert ("detail" in r.json()) or ("Status" in r.json())

    # shop GET
    r = api_client.get("/api/partner/shop/")
    assert r.status_code in (401, 403), r.json()
    assert ("detail" in r.json()) or ("Status" in r.json())

    # orders GET
    r = api_client.get("/api/partner/orders/")
    assert r.status_code in (401, 403), r.json()
    assert ("detail" in r.json()) or ("Status" in r.json())


@pytest.mark.django_db
def test_partner_endpoints_only_for_suppliers(client_api):
    # client_api authenticated but role=client -> permission denied
    r = client_api.post("/api/partner/state/", {"state": True}, format="json")
    assert r.status_code == 403, r.json()
    # permission denied often returns {"detail": "..."}
    assert ("detail" in r.json()) or (r.json().get("Status") is False)

    r = client_api.get("/api/partner/orders/")
    assert r.status_code == 403, r.json()
    assert ("detail" in r.json()) or (r.json().get("Status") is False)


@pytest.mark.django_db
def test_partner_orders_total_branch(supplier_api, supplier_user, client_user):
    shop = Shop.objects.create(name="TotalShop", url="https://t.test", state=True, user=supplier_user)
    cat = Category.objects.create(name="TotalCat")
    product = Product.objects.create(category=cat, name="TotalProd")

    order = Order.objects.create(user=client_user, status=Order.Status.NEW, dt=timezone.now())
    OrderItem.objects.create(
        order=order,
        product=product,
        shop=shop,
        quantity=2,
        unit_price="10.00",
        unit_price_rrc="12.00",
    )

    r = supplier_api.get("/api/partner/orders/")
    assert r.status_code == 200, r.json()
    body = r.json()
    assert body.get("Status") is True  # тут уже unified
    item = body["data"]["orders"][0]["items"][0]
    assert item["total"] is not None