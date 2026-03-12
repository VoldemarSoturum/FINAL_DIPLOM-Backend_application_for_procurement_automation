# tests/test_config_urls.py

import importlib
import sys

import pytest
from django.test import Client, override_settings


@pytest.mark.django_db
def test_config_urls_contains_expected_routes_and_debug_media(tmp_path):
    """
    Цели:
    - выполнить строки в config/urls.py, которые добавляют include-роуты (baton, social-auth, etc.)
    - выполнить health view ("" -> {"status": "ok"})
    - выполнить DEBUG-блок со static(settings.MEDIA_URL, ...) (обычно это "хвост" urls.py)

    Особенность:
    - django.conf.urls.static.static() часто возвращает regex-паттерн вида:
      '^media/(?P<path>.*)$'
      поэтому проверяем НЕ только 'media/', но и '^media/'.
    - раздача media возвращает FileResponse (streaming) -> читаем через streaming_content.
    """
    with override_settings(
        DEBUG=True,
        MEDIA_URL="/media/",
        MEDIA_ROOT=tmp_path,
        ROOT_URLCONF="config.urls",
    ):
        # ВАЖНО: переимпорт, чтобы DEBUG-блок в urls.py выполнился заново
        sys.modules.pop("config.urls", None)
        import config.urls as urls_mod  # noqa: F401
        importlib.reload(urls_mod)

        patterns = [str(p.pattern) for p in urls_mod.urlpatterns]

        # root health route pattern присутствует
        assert "" in patterns

        # baton include присутствует (если действительно подключён)
        assert any(p.startswith("baton/") for p in patterns), patterns

        # social urls include присутствует (если действительно подключён)
        assert any(p.startswith("api/auth/social/") for p in patterns), patterns

        # DEBUG media serve: допускаем regex-вариант static()
        assert any(
            p.startswith("media/") or p.startswith("^media/") or "media/" in p
            for p in patterns
        ), patterns

        c = Client()

        # 1) health реально выполняется (покрываем тело функции health)
        r0 = c.get("/")
        assert r0.status_code == 200
        assert r0.json() == {"status": "ok"}

        # 2) media serve реально работает (200) на существующем файле
        (tmp_path / "x.txt").write_text("ok", encoding="utf-8")

        r = c.get("/media/x.txt")
        assert r.status_code == 200

        # FileResponse => это streaming, читаем через streaming_content
        body = b"".join(r.streaming_content)
        assert body == b"ok"