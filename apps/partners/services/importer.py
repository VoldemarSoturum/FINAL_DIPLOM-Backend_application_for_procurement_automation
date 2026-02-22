from __future__ import annotations

from decimal import Decimal
from typing import Any

import requests
import yaml
from django.db import transaction

from apps.catalog.models import Category, Parameter, Product, ProductInfo, ProductParameter, Shop


def import_price_from_url(*, user, url: str) -> dict[str, Any]:
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        return {"Status": False, "Error": f"Failed to fetch url: {e}", "http_status": 400}

    try:
        data = yaml.safe_load(resp.content)
    except Exception as e:
        return {"Status": False, "Error": f"Invalid YAML: {e}", "http_status": 400}

    if not isinstance(data, dict) or "shop" not in data or "categories" not in data or "goods" not in data:
        return {"Status": False, "Error": "YAML must contain keys: shop, categories, goods", "http_status": 400}

    shop_name = data["shop"]
    categories = data["categories"] or []
    goods = data["goods"] or []

    # В YAML категория у товара задаётся ID -> делаем маппинг id -> name
    cat_id_to_name: dict[int, str] = {}
    for c in categories:
        try:
            cat_id_to_name[int(c["id"])] = str(c["name"])
        except Exception:
            continue

    with transaction.atomic():
        shop, _ = Shop.objects.get_or_create(name=shop_name)
        # Привязываем магазин к текущему поставщику (если пусто)
        if shop.user_id is None:
            shop.user = user
            shop.url = url  # можно хранить "последний импорт"
            shop.save(update_fields=["user", "url"])
        elif shop.user_id != user.id:
            return {"Status": False, "Error": "This shop belongs to another supplier", "http_status": 403}

        # Категории + связь с магазином
        for _, cat_name in cat_id_to_name.items():
            category_obj, _ = Category.objects.get_or_create(name=cat_name)
            category_obj.shops.add(shop)

        imported_external_ids: set[int] = set()

        # Товары
        for item in goods:
            try:
                external_id = int(item["id"])
                cat_id = int(item["category"])
                name = str(item["name"])
                model = str(item.get("model", ""))

                price = Decimal(str(item["price"]))
                price_rrc = item.get("price_rrc")
                price_rrc = Decimal(str(price_rrc)) if price_rrc is not None else None

                quantity = int(item.get("quantity", 0))
                params = item.get("parameters") or {}
            except Exception as e:
                return {"Status": False, "Error": f"Bad goods item: {e}", "http_status": 400}

            category_name = cat_id_to_name.get(cat_id)
            if not category_name:
                return {"Status": False, "Error": f"Category id={cat_id} not found in YAML categories", "http_status": 400}

            category_obj, _ = Category.objects.get_or_create(name=category_name)

            product, _ = Product.objects.get_or_create(category=category_obj, name=name)

            product_info, created = ProductInfo.objects.get_or_create(
                shop=shop,
                external_id=external_id,
                defaults={
                    "product": product,
                    "name": name,
                    "model": model,
                    "quantity": quantity,
                    "price": price,
                    "price_rrc": price_rrc,
                },
            )
            if not created:
                # Обновление прайса
                product_info.product = product
                product_info.name = name
                product_info.model = model
                product_info.quantity = quantity
                product_info.price = price
                product_info.price_rrc = price_rrc
                product_info.save()

            imported_external_ids.add(external_id)

            # Параметры товара
            if isinstance(params, dict):
                for p_name, p_value in params.items():
                    parameter_obj, _ = Parameter.objects.get_or_create(name=str(p_name))

                    ProductParameter.objects.update_or_create(
                        product_info=product_info,
                        parameter=parameter_obj,
                        defaults={"value": str(p_value)},
                    )

        # Если позиция исчезла из прайса — обнуляем остаток, но НЕ удаляем запись
        ProductInfo.objects.filter(shop=shop).exclude(external_id__in=imported_external_ids).update(quantity=0)

    return {"Status": True}