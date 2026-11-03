"""Bulgu (Finding) yönetimi.

CLAUDE.md kuralı: 'Şüpheli bulguyu doğrulanmış gibi sunma; iddiaları
kanıtla ilişkilendir.' Bu yüzden risk_level/status alanları serbest
metin değil, sabit enum'lardır ve varsayılan durum her zaman
`suspected`dır — hiçbir bulgu doğrudan 'confirmed' olarak oluşturulamaz,
yalnızca Validation akışıyla (ileride) durum değiştirilir."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models import Asset, Finding, FindingStatus, Project, RiskLevel, User
from app.services.audit import record_audit_event
from app.services.auth import get_current_user

router = APIRouter(prefix="/findings", tags=["findings"])


class FindingCreate(BaseModel):
    project_id: str
    asset_id: str | None = None
    title: str
    description: str
    risk_level: RiskLevel | None = None


class FindingUpdate(BaseModel):
    status: FindingStatus | None = None
    risk_level: RiskLevel | None = None


class FindingOut(BaseModel):
    id: str
    project_id: str
    asset_id: str | None
    title: str
    description: str
    status: FindingStatus
    risk_level: RiskLevel | None

    model_config = ConfigDict(from_attributes=True)


@router.get("", response_model=list[FindingOut])
async def list_findings(
    project_id: str, db: AsyncSession = Depends(get_db)
) -> list[Finding]:
    result = await db.execute(select(Finding).where(Finding.project_id == project_id))
    return list(result.scalars().all())


@router.post("", response_model=FindingOut, status_code=201)
async def create_finding(
    payload: FindingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Finding:
    project = await db.get(Project, payload.project_id)
    if project is None:
        raise HTTPException(404, "Proje bulunamadı.")
    if payload.asset_id is not None:
        asset = await db.get(Asset, payload.asset_id)
        if asset is None or asset.project_id != project.id:
            raise HTTPException(404, "Varlık bu projede bulunamadı.")

    finding = Finding(
        project_id=payload.project_id,
        asset_id=payload.asset_id,
        title=payload.title,
        description=payload.description,
        risk_level=payload.risk_level,
        status=FindingStatus.SUSPECTED,
    )
    db.add(finding)
    await record_audit_event(
        db,
        actor=current_user.email,
        action="finding.created",
        project_id=project.id,
        details={"title": payload.title, "risk_level": payload.risk_level},
    )
    await db.commit()
    await db.refresh(finding)
    return finding


@router.patch("/{finding_id}", response_model=FindingOut)
async def update_finding(
    finding_id: str,
    payload: FindingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Finding:
    finding = await db.get(Finding, finding_id)
    if finding is None:
        raise HTTPException(404, "Bulgu bulunamadı.")

    changes: dict = {}
    if payload.status is not None:
        changes["status"] = {"from": finding.status.value, "to": payload.status.value}
        finding.status = payload.status
    if payload.risk_level is not None:
        changes["risk_level"] = {
            "from": finding.risk_level.value if finding.risk_level else None,
            "to": payload.risk_level.value,
        }
        finding.risk_level = payload.risk_level

    if changes:
        await record_audit_event(
            db,
            actor=current_user.email,
            action="finding.updated",
            project_id=finding.project_id,
            details={"finding_id": finding.id, **changes},
        )
    await db.commit()
    await db.refresh(finding)
    return finding
