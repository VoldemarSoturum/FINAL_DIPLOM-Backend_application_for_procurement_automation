import logging
import pytest

from apps.catalog.models import Category, Shop, Product, ProductInfo

logger = logging.getLogger(__name__)


@pytest.mark.django_db
def test_catalog_products_filters_and_search(api_client):
    """
    Покрываем:
    - category filter
    - shop filter
    - in_stock filter
    - q search (name/model)
    - ordering (устойчиво к разным collation/регистрам)
    - detail endpoint (offers + external_id)
    """
    # ---------------------------
    # Arrange: shops + categories
    # ---------------------------
    shop_a = Shop.objects.create(name="ShopA", url="https://a.test", state=True)
    shop_b = Shop.objects.create(name="ShopB", url="https://b.test", state=True)

    cat_phones = Category.objects.create(name="Phones")
    cat_tv = Category.objects.create(name="TV")
    cat_phones.shops.add(shop_a, shop_b)
    cat_tv.shops.add(shop_a)

    # ---------------------------
    # Arrange: products + offers
    # ---------------------------
    p1 = Product.objects.create(category=cat_phones, name="iPhone 15")
    p2 = Product.objects.create(category=cat_phones, name="Pixel 9")
    p3 = Product.objects.create(category=cat_tv, name="Samsung TV")

    ProductInfo.objects.create(
        product=p1,
        shop=shop_a,
        external_id=1001,
        model="A1",
        name="iPhone offer A",
        quantity=10,
        price="100.00",
        price_rrc="120.00",
    )
    ProductInfo.objects.create(
        product=p1,
        shop=shop_b,
        external_id=1002,
        model="A2",
        name="iPhone offer B",
        quantity=0,
        price="90.00",
        price_rrc="110.00",
    )
    ProductInfo.objects.create(
        product=p2,
        shop=shop_a,
        external_id=2001,
        model="P9",
        name="Pixel offer",
        quantity=5,
        price="50.00",
        price_rrc="60.00",
    )
    ProductInfo.objects.create(
        product=p3,
        shop=shop_a,
        external_id=3001,
        model="TVX",
        name="TV offer",
        quantity=1,
        price="300.00",
        price_rrc="350.00",
    )

    # ---------------------------
    # Act/Assert: categories list
    # ---------------------------
    logger.info("GET categories")
    r = api_client.get("/api/catalog/categories/")
    assert r.status_code == 200
    names = [c["name"] for c in r.json()]
    assert "Phones" in names and "TV" in names

    # ---------------------------
    # Act/Assert: shops list
    # ---------------------------
    logger.info("GET shops")
    r = api_client.get("/api/catalog/shops/")
    assert r.status_code == 200
    shop_names = [s["name"] for s in r.json()]
    assert "ShopA" in shop_names and "ShopB" in shop_names

    # ---------------------------
    # Act/Assert: filter by category
    # ---------------------------
    logger.info("Filter by category=Phones")
    r = api_client.get(f"/api/catalog/products/?category={cat_phones.id}")
    assert r.status_code == 200
    returned_names = {p["name"] for p in r.json()}
    assert returned_names == {"iPhone 15", "Pixel 9"}

    # ---------------------------
    # Act/Assert: filter by shop
    # ---------------------------
    logger.info("Filter by shop=ShopB -> only iPhone 15 has offer in ShopB")
    r = api_client.get(f"/api/catalog/products/?shop={shop_b.id}")
    assert r.status_code == 200
    returned_names = {p["name"] for p in r.json()}
    assert returned_names == {"iPhone 15"}

    # ---------------------------
    # Act/Assert: filter in_stock
    # ---------------------------
    logger.info("Filter in_stock=1 -> products with any offer qty>0")
    r = api_client.get("/api/catalog/products/?in_stock=1")
    assert r.status_code == 200
    returned_names = {p["name"] for p in r.json()}
    assert returned_names == {"iPhone 15", "Pixel 9", "Samsung TV"}

    # ---------------------------
    # Act/Assert: search by model/name/offer name
    # ---------------------------
    logger.info("Search q=A1 (model) -> iPhone 15")
    r = api_client.get("/api/catalog/products/?q=A1")
    assert r.status_code == 200
    returned_names = {p["name"] for p in r.json()}
    assert returned_names == {"iPhone 15"}

    # ---------------------------
    # Act/Assert: ordering
    # ВАЖНО: не фиксируем конкретный "первый" элемент.
    # На разных окружениях/БД collation может отличаться (регистр/локаль),
    # поэтому проверяем, что ordering реально меняет порядок и что
    # -name является обратным name.
    # ---------------------------
    logger.info("Ordering: name and -name should be reverse lists")
    r_asc = api_client.get("/api/catalog/products/?ordering=name")
    assert r_asc.status_code == 200
    asc = [p["name"] for p in r_asc.json()]

    r_desc = api_client.get("/api/catalog/products/?ordering=-name")
    assert r_desc.status_code == 200
    desc = [p["name"] for p in r_desc.json()]

    assert set(asc) == {"iPhone 15", "Pixel 9", "Samsung TV"}
    assert set(desc) == set(asc)
    assert desc == list(reversed(asc)), {"asc": asc, "desc": desc}

    # ---------------------------
    # Act/Assert: detail endpoint
    # ---------------------------
    logger.info("Product detail includes offers")
    r = api_client.get(f"/api/catalog/products/{p1.id}/")
    assert r.status_code == 200
    detail = r.json()
    assert detail["name"] == "iPhone 15"
    assert "offers" in detail
    assert len(detail["offers"]) == 2
    assert any(o["external_id"] == 1001 for o in detail["offers"])