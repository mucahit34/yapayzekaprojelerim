"""Görev oluşturma: aktif test/dış hedefe trafik gerektiren her görev,
kapsam kontrolünden geçmeli ve audit log'a yazılmalıdır (bkz. CLAUDE.md
kural: 'Her yüksek etkili işlemden önce gerekçeyi, etkiyi ve geri dönüş
planını açıkla ve onay bekle')."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models import Asset, Project, Task, TaskStatus, User
from app.services.audit import record_audit_event
from app.services.auth import get_current_user
from app.services.scope import check_scope

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskCreate(BaseModel):
    project_id: str
    asset_id: str
    title: str
    agent_role: str


class TaskOut(BaseModel):
    id: str
    project_id: str
    title: str
    agent_role: str
    status: TaskStatus
    requires_approval: bool

    model_config = ConfigDict(from_attributes=True)


@router.post("", response_model=TaskOut, status_code=201)
async def create_task(
    payload: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Task:
    project = await db.get(Project, payload.project_id)
    if project is None:
        raise HTTPException(404, "Proje bulunamadı.")

    asset = await db.get(Asset, payload.asset_id)
    if asset is None or asset.project_id != project.id:
        raise HTTPException(404, "Varlık bu projede bulunamadı.")

    decision = check_scope(project.scope_definition, asset.identifier)

    if not asset.in_scope or not decision.allowed:
        await record_audit_event(
            db,
            actor=current_user.email,
            action="task.rejected_out_of_scope",
            project_id=project.id,
            details={
                "asset_id": asset.id,
                "identifier": asset.identifier,
                "reason": decision.reason,
                "asset_in_scope_flag": asset.in_scope,
            },
        )
        await db.commit()
        raise HTTPException(
            403,
            f"Bu hedef yetkili kapsamda değil: {decision.reason}",
        )

    task = Task(
        project_id=project.id,
        title=payload.title,
        agent_role=payload.agent_role,
        status=TaskStatus.AWAITING_APPROVAL,
        requires_approval=True,
    )
    db.add(task)
    await record_audit_event(
        db,
        actor=current_user.email,
        action="task.created_awaiting_approval",
        project_id=project.id,
        details={"asset_id": asset.id, "identifier": asset.identifier, "title": payload.title},
    )
    await db.commit()
    await db.refresh(task)
    return task


@router.post("/{task_id}/approve", response_model=TaskOut)
async def approve_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Task:
    """Onaylayan kimliği artık istemcinin gönderdiği serbest metinden değil,
    JWT token'ından (get_current_user) gelir — bkz. app/services/auth.py."""
    task = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(404, "Görev bulunamadı.")
    if task.status != TaskStatus.AWAITING_APPROVAL:
        raise HTTPException(409, f"Görev onay bekleyen durumda değil (durum: {task.status}).")

    task.status = TaskStatus.PENDING
    task.approved_by = current_user.email
    task.approved_at = datetime.now(timezone.utc)

    await record_audit_event(
        db,
        actor=current_user.email,
        action="task.approved",
        project_id=task.project_id,
        details={"task_id": task.id},
    )
    await db.commit()
    await db.refresh(task)
    return task


@router.get("", response_model=list[TaskOut])
async def list_tasks(project_id: str, db: AsyncSession = Depends(get_db)) -> list[Task]:
    result = await db.execute(select(Task).where(Task.project_id == project_id))
    return list(result.scalars().all())
