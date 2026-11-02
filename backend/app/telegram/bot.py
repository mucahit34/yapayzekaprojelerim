"""Telegram bot: web paneliyle aynı backend/veri modelini paylaşan,
whitelist ile korunan komut arayüzü.

Çalıştırma: `python -m app.telegram.bot` (ayrı bir süreç olarak; FastAPI
uygulamasından bağımsız, polling modunda). TELEGRAM_BOT_TOKEN ve
TELEGRAM_ALLOWED_USER_IDS ortam değişkenlerinden okunur, hiçbir zaman
loglanmaz veya kullanıcıya geri yansıtılmaz."""
from __future__ import annotations

import functools
import logging
from collections.abc import Awaitable, Callable

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from app.core.config import get_settings
from app.core.db import AsyncSessionLocal
from app.telegram.access import actor_for, is_allowed_telegram_user
from app.telegram.service import (
    CommandError,
    approve_task,
    create_project,
    find_project,
    list_projects,
    list_tasks,
)

logger = logging.getLogger(__name__)

Handler = Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]]


def require_allowed(handler: Handler) -> Handler:
    @functools.wraps(handler)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not is_allowed_telegram_user(user.id if user else None):
            # Whitelist dışı kullanıcıya hiçbir yanıt verilmez — bot'un
            # varlığı veya komut seti açık edilmez.
            logger.warning("İzinsiz Telegram erişimi denemesi: user_id=%s", user.id if user else None)
            return
        await handler(update, context)

    return wrapped


@require_allowed
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Kişisel AI Güvenlik Asistanı\n\n"
        "/projeler — projeleri listele\n"
        "/yeni_proje <ad> — proje oluştur (kapsam web panelinden tanımlanır)\n"
        "/gorevler <proje adı veya id> — görev durumunu listele\n"
        "/onayla <task_id> — onay bekleyen görevi onayla"
    )


@require_allowed
async def projects_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with AsyncSessionLocal() as db:
        projects = await list_projects(db)
    if not projects:
        await update.message.reply_text("Henüz proje yok. /yeni_proje <ad> ile oluşturun.")
        return
    lines = [f"• {p.name}  ({p.id[:8]})" for p in projects]
    await update.message.reply_text("Projeler:\n" + "\n".join(lines))


@require_allowed
async def new_project_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    name = " ".join(context.args) if context.args else ""
    actor = actor_for(update.effective_user.id)
    try:
        async with AsyncSessionLocal() as db:
            project = await create_project(db, name=name, actor=actor)
    except CommandError as exc:
        await update.message.reply_text(str(exc))
        return
    await update.message.reply_text(
        f"Proje oluşturuldu: {project.name} ({project.id[:8]}).\n"
        "Kapsamı (izinli hedefler) tanımlamadan hiçbir aktif test görevi "
        "onaylanmaz — web panelinden ekleyin."
    )


@require_allowed
async def tasks_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Kullanım: /gorevler <proje adı veya id>")
        return
    identifier = " ".join(context.args)
    async with AsyncSessionLocal() as db:
        project = await find_project(db, identifier)
        if project is None:
            await update.message.reply_text(
                f"'{identifier}' ile eşleşen tek bir proje bulunamadı."
            )
            return
        tasks = await list_tasks(db, project)
    if not tasks:
        await update.message.reply_text(f"{project.name}: henüz görev yok.")
        return
    lines = [f"• [{t.status.value}] {t.title}  (id: {t.id[:8]})" for t in tasks]
    await update.message.reply_text(f"{project.name} — görevler:\n" + "\n".join(lines))


@require_allowed
async def approve_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Kullanım: /onayla <task_id>")
        return
    task_id = context.args[0]
    actor = actor_for(update.effective_user.id)
    try:
        async with AsyncSessionLocal() as db:
            task = await approve_task(db, task_id=task_id, actor=actor)
    except CommandError as exc:
        await update.message.reply_text(str(exc))
        return
    await update.message.reply_text(f"Onaylandı: {task.title} (durum: {task.status.value}).")


def build_application() -> Application:
    settings = get_settings()
    if not settings.telegram_bot_token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN ayarlı değil. Bot başlatılamaz."
        )
    app = Application.builder().token(settings.telegram_bot_token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("projeler", projects_cmd))
    app.add_handler(CommandHandler("yeni_proje", new_project_cmd))
    app.add_handler(CommandHandler("gorevler", tasks_cmd))
    app.add_handler(CommandHandler("onayla", approve_cmd))
    return app


def main() -> None:  # pragma: no cover - gerçek polling döngüsü
    logging.basicConfig(level=logging.INFO)
    app = build_application()
    logger.info("Telegram bot polling modunda başlatılıyor.")
    app.run_polling()


if __name__ == "__main__":  # pragma: no cover
    main()
