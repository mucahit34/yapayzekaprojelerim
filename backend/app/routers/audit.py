"""Audit log'u salt-okunur olarak dışa verir — dashboard'daki 'son
etkinlik' akışı için. Hiçbir yazma işlemi burada yapılmaz; AuditEvent
kayıtları zaten diğer tüm router'larda (projects, tasks, findings,
reports, auth) her yüksek etkili işlemde otomatik oluşturuluyor."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models import AuditEvent

router = APIRouter(prefix="/audit", tags=["audit"])


class AuditEventOut(BaseModel):
    id: str
    project_id: str | None
    actor: str
    action: str
    details: dict
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


@router.get("", response_model=list[AuditEventOut])
async def list_audit_events(
    project_id: str | None = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
) -> list[AuditEvent]:
    limit = max(1, min(limit, 100))
    query = select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(limit)
    if project_id:
        query = query.where(AuditEvent.project_id == project_id)
    result = await db.execute(query)
    return list(result.scalars().all())
