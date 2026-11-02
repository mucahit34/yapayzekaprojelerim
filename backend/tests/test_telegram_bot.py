import pytest


def test_build_application_requires_token(monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "")
    get_settings.cache_clear()
    try:
        from app.telegram.bot import build_application

        with pytest.raises(RuntimeError):
            build_application()
    finally:
        get_settings.cache_clear()


def test_build_application_registers_all_commands(monkeypatch):
    from app.core.config import get_settings

    # python-telegram-bot gerçek bir token formatı bekler ama ağa bağlanmaz;
    # Application.builder().build() yalnızca nesneleri kurar.
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:fake-token-for-tests")
    get_settings.cache_clear()
    try:
        from app.telegram.bot import build_application

        app = build_application()
        # CommandHandler.commands, her handler için bir frozenset'tir.
        all_commands = set()
        for group in app.handlers.values():
            for handler in group:
                all_commands |= getattr(handler, "commands", set())
        assert {"start", "projeler", "yeni_proje", "gorevler", "onayla"} <= all_commands
    finally:
        get_settings.cache_clear()
