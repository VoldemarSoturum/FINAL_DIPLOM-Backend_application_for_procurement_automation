import importlib
import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model

from apps.users.models import UserProfile, Contact


@pytest.mark.django_db
def test_users_admin_hits_notregistered_branch_22_23():
    User = get_user_model()

    # перед reload гарантируем, что модель НЕ зарегистрирована,
    # чтобы внутри admin.py unregister(User) бросил NotRegistered (и выполнились 22-23)
    for m in (User, UserProfile, Contact):
        try:
            admin.site.unregister(m)
        except admin.sites.NotRegistered:
            pass

    import apps.users.admin as users_admin
    importlib.reload(users_admin)  # теперь пройдет ветка except NotRegistered: pass