# autodiscover for user tasks about avatars

from __future__ import annotations

from celery import shared_task
from versatileimagefield.image_warmer import VersatileImageFieldWarmer

from apps.users.models import UserProfile


@shared_task(name="apps.users.tasks.warm_user_avatar_renditions")
def warm_user_avatar_renditions(profile_id: int) -> dict:
    profile = UserProfile.objects.filter(id=profile_id).first()
    if not profile or not profile.avatar:
        return {"Status": False, "Error": "Profile or avatar not found"}

    warmer = VersatileImageFieldWarmer(
        instance_or_queryset=profile,
        rendition_key_set="avatar",
        image_attr="avatar",
    )
    num_created, failed = warmer.warm()
    warmer.clear()  # чистим ссылки из cache warmer-а
    return {"Status": True, "created": num_created, "failed": len(failed)}