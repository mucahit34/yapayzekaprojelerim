from app.telegram.access import actor_for, is_allowed_telegram_user


def test_empty_whitelist_denies_everyone(monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setenv("TELEGRAM_ALLOWED_USER_IDS", "")
    get_settings.cache_clear()
    assert is_allowed_telegram_user(12345) is False
    get_settings.cache_clear()


def test_id_in_whitelist_allowed(monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setenv("TELEGRAM_ALLOWED_USER_IDS", "111,222,333")
    get_settings.cache_clear()
    assert is_allowed_telegram_user(222) is True
    assert is_allowed_telegram_user(999) is False
    get_settings.cache_clear()


def test_none_user_id_denied(monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setenv("TELEGRAM_ALLOWED_USER_IDS", "111")
    get_settings.cache_clear()
    assert is_allowed_telegram_user(None) is False
    get_settings.cache_clear()


def test_actor_for_format():
    assert actor_for(42) == "telegram:42"
