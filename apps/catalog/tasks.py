# autodiscover for tasks catalog images staff
from __future__ import annotations

from celery import shared_task
from versatileimagefield.image_warmer import VersatileImageFieldWarmer

from apps.catalog.models import Product


@shared_task(name="apps.catalog.tasks.warm_product_image_renditions")
def warm_product_image_renditions(product_id: int) -> dict:
    product = Product.objects.filter(id=product_id).first()
    if not product or not product.image:
        return {"Status": False, "Error": "Product or image not found"}

    warmer = VersatileImageFieldWarmer(
        instance_or_queryset=product,
        rendition_key_set="product",
        image_attr="image",
    )
    num_created, failed = warmer.warm()
    warmer.clear()
    return {"Status": True, "created": num_created, "failed": len(failed)}