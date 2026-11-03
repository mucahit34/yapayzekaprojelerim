def test_cors_allowed_origins_list_parses_comma_separated(monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS", "http://localhost:8081, http://127.0.0.1:8081"
    )
    get_settings.cache_clear()
    try:
        settings = get_settings()
        assert settings.cors_allowed_origins_list == [
            "http://localhost:8081",
            "http://127.0.0.1:8081",
        ]
    finally:
        get_settings.cache_clear()


def test_cors_allowed_origins_default_is_local_dev_only():
    from app.core.config import get_settings

    get_settings.cache_clear()
    try:
        settings = get_settings()
        assert settings.cors_allowed_origins_list == [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    finally:
        get_settings.cache_clear()
