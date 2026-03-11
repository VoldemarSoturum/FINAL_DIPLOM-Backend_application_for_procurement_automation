from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import UserProfile
from apps.users.tasks import warm_user_avatar_renditions

User = get_user_model()


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=UserProfile)
def enqueue_avatar_warmup(sender, instance: UserProfile, **kwargs):
    # Если аватар не задан — ничего не делаем
    if not instance.avatar:
        return

    # Важно: только после коммита, чтобы файл/строка в БД уже точно были.
    transaction.on_commit(lambda: warm_user_avatar_renditions.delay(instance.id))