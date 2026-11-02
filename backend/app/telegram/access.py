"""Telegram erişim kontrolü.

Telegram tarafında JWT akışı yok; tek güvenlik katmanı
`TELEGRAM_ALLOWED_USER_IDS` whitelist'idir. Bu listede olmayan hiçbir
Telegram kullanıcısı hiçbir komuta yanıt alamaz — whitelist dışı bir
mesaj sessizce yok sayılır (bot'un var olduğunu veya hangi komutları
desteklediğini dahi açık etmez)."""
from __future__ import annotations

from app.core.config import get_settings


def is_allowed_telegram_user(telegram_user_id: int | None) -> bool:
    if telegram_user_id is None:
        return False
    allowed = get_settings().telegram_allowed_ids
    if not allowed:
        # Whitelist boşsa fail-closed: kimse izinli değildir. Boş whitelist
        # 'herkese açık' anlamına gelmemeli.
        return False
    return telegram_user_id in allowed


def actor_for(telegram_user_id: int) -> str:
    """Audit log'larda kullanılan aktör kimliği — web tarafındaki e-posta
    yerine kanal + Telegram user ID ile ayrıştırılabilir olsun."""
    return f"telegram:{telegram_user_id}"
