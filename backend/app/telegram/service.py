"""Telegram komutlarının kullandığı veri işlemleri.

Bilinçli tasarım: bu fonksiyonlar HTTP üzerinden /api'ye istek atmaz,
doğrudan aynı backend'in servis katmanını (app.services.*) ve veri
modelini kullanır — web paneli ile Telegram, CLAUDE.md'nin istediği gibi
'aynı backend, koordinatör, proje hafızası'nı paylaşır, ayrı bir mantık
tekrar yazılmaz."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Project, Task, TaskStatus
from app.services.audit import record_audit_event


class CommandError(Exception):
    """Kullanıcıya olduğu gibi gösterilecek, beklenen/öngörülen hatalar."""


async def list_projects(db: AsyncSession) -> list[Project]:
    result = await db.execute(select(Project).where(Project.is_archived.is_(False)))
    return list(result.scalars().all())


async def create_project(db: AsyncSession, *, name: str, actor: str) -> Project:
    name = name.strip()
    if not name:
        raise CommandError("Proje adı boş olamaz.")
    # Kapsam (scope_definition) kasıtlı olarak boş bırakılır: fail-closed
    # tasarım gereği boş kapsam = hiçbir hedef izinli değil. Kapsamı
    # tanımlamak, yanlışlıkla elden yazılan bir metinle değil, web
    # panelindeki yapılandırılmış formla yapılmalı.
    project = Project(name=name, scope_definition={})
    db.add(project)
    await record_audit_event(
        db, actor=actor, action="project.created_via_telegram", details={"name": name}
    )
    await db.commit()
    await db.refresh(project)
    return project


async def find_project(db: AsyncSession, identifier: str) -> Project | None:
    """Tam ID, ID ÖNEKİ (bot kullanıcıya her zaman 8 karakterlik kısaltılmış
    ID gösterir — bkz. bot.py) veya (tam/kısmi, büyük-küçük harf duyarsız)
    isimle proje bulur."""
    identifier = identifier.strip()
    if not identifier:
        return None
    by_id = await db.get(Project, identifier)
    if by_id is not None:
        return by_id
    result = await db.execute(
        select(Project)
        .where(Project.id.like(f"{identifier}%") | Project.name.ilike(f"%{identifier}%"))
        .limit(2)
    )
    matches = result.scalars().all()
    if len(matches) == 1:
        return matches[0]
    return None


async def list_tasks(db: AsyncSession, project: Project) -> list[Task]:
    result = await db.execute(select(Task).where(Task.project_id == project.id))
    return list(result.scalars().all())


async def find_task(db: AsyncSession, identifier: str) -> Task | None:
    """Tam ID veya ID ÖNEKİYLE (bot kullanıcıya 8 karakterlik kısaltılmış ID
    gösterir) görev bulur."""
    identifier = identifier.strip()
    if not identifier:
        return None
    by_id = await db.get(Task, identifier)
    if by_id is not None:
        return by_id
    result = await db.execute(select(Task).where(Task.id.like(f"{identifier}%")).limit(2))
    matches = result.scalars().all()
    if len(matches) == 1:
        return matches[0]
    return None


async def approve_task(db: AsyncSession, *, task_id: str, actor: str) -> Task:
    task = await find_task(db, task_id)
    if task is None:
        raise CommandError(f"'{task_id}' kimliğiyle bir görev bulunamadı.")
    if task.status != TaskStatus.AWAITING_APPROVAL:
        raise CommandError(f"Bu görev onay bekleyen durumda değil (durum: {task.status.value}).")

    import datetime as dt

    task.status = TaskStatus.PENDING
    task.approved_by = actor
    task.approved_at = dt.datetime.now(dt.timezone.utc)

    await record_audit_event(
        db,
        actor=actor,
        action="task.approved",
        project_id=task.project_id,
        details={"task_id": task.id, "channel": "telegram"},
    )
    await db.commit()
    await db.refresh(task)
    return task
