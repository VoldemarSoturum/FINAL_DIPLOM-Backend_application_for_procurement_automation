from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.catalog.models import Product
from apps.catalog.tasks import warm_product_image_renditions


@receiver(post_save, sender=Product)
def enqueue_product_image_warmup(sender, instance: Product, **kwargs):
    if not instance.image:
        return
    transaction.on_commit(lambda: warm_product_image_renditions.delay(instance.id))