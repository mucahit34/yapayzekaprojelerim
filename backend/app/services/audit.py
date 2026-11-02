"""Her yüksek etkili/aktif test işlemi için zorunlu audit kaydı yardımcıları."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditEvent


async def record_audit_event(
    db: AsyncSession,
    *,
    actor: str,
    action: str,
    project_id: str | None = None,
    details: dict | None = None,
) -> AuditEvent:
    event = AuditEvent(
        actor=actor,
        action=action,
        project_id=project_id,
        details=details or {},
    )
    db.add(event)
    await db.flush()
    return event
