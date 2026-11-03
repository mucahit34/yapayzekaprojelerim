"""Rapor kalıcılığı.

Report.data_snapshot, rapor stüdyosunun o anki durumunu (şablon +
bölümler) tutar — PDF her zaman bu kayıtlı durumdan üretilir, canlı
düzenleme state'inden değil (README'deki 'raporlar sabitlenmiş veri
snapshot'ıyla üretilir' kuralı).

ReportRevision, AI'nin önerdiği değişiklikleri denetlenebilir bir
geçmiş olarak tutar: her taslak `is_ai_draft=True, approved=False`
olarak kaydedilir; yalnızca `/approve` çağrısı onu Report.data_snapshot'a
yazar (CLAUDE.md: 'AI değişiklikleri önce taslak olmalı ve onayla
uygulanmalı')."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models import Project, Report, ReportRevision, User
from app.services.audit import record_audit_event
from app.services.auth import get_current_user
from app.services.pdf import PdfRenderError, render_report_pdf

router = APIRouter(prefix="/reports", tags=["reports"])


class ReportUpsert(BaseModel):
    project_id: str
    template: str
    data_snapshot: dict


class ReportOut(BaseModel):
    id: str
    project_id: str
    template: str
    data_snapshot: dict

    model_config = ConfigDict(from_attributes=True)


class RevisionCreate(BaseModel):
    content: dict
    is_ai_draft: bool = False


class RevisionOut(BaseModel):
    id: str
    report_id: str
    content: dict
    is_ai_draft: bool
    approved: bool
    created_by: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


@router.get("", response_model=list[ReportOut])
async def list_reports(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[Report]:
    result = await db.execute(select(Report).where(Report.project_id == project_id))
    return list(result.scalars().all())


@router.put("", response_model=ReportOut)
async def upsert_report(
    payload: ReportUpsert,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Report:
    """Proje+şablon başına TEK rapor (upsert). Çoklu sürüm geçmişi
    ReportRevision üzerinden tutulur; burada yalnızca 'o an geçerli olan'
    durum güncellenir."""
    project = await db.get(Project, payload.project_id)
    if project is None:
        raise HTTPException(404, "Proje bulunamadı.")

    result = await db.execute(
        select(Report).where(
            Report.project_id == payload.project_id, Report.template == payload.template
        )
    )
    report = result.scalar_one_or_none()
    action = "report.updated"
    if report is None:
        report = Report(project_id=payload.project_id, template=payload.template)
        db.add(report)
        action = "report.created"

    report.data_snapshot = payload.data_snapshot
    await record_audit_event(
        db,
        actor=current_user.email,
        action=action,
        project_id=project.id,
        details={"template": payload.template},
    )
    await db.commit()
    await db.refresh(report)
    return report


@router.post("/{report_id}/revisions", response_model=RevisionOut, status_code=201)
async def create_revision(
    report_id: str,
    payload: RevisionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportRevision:
    report = await db.get(Report, report_id)
    if report is None:
        raise HTTPException(404, "Rapor bulunamadı.")
    revision = ReportRevision(
        report_id=report_id,
        content=payload.content,
        is_ai_draft=payload.is_ai_draft,
        created_by=current_user.email,
    )
    db.add(revision)
    await record_audit_event(
        db,
        actor=current_user.email,
        action="report_revision.created",
        project_id=report.project_id,
        details={"report_id": report_id, "is_ai_draft": payload.is_ai_draft},
    )
    await db.commit()
    await db.refresh(revision)
    return revision


@router.get("/{report_id}/revisions", response_model=list[RevisionOut])
async def list_revisions(
    report_id: str, db: AsyncSession = Depends(get_db)
) -> list[ReportRevision]:
    result = await db.execute(
        select(ReportRevision)
        .where(ReportRevision.report_id == report_id)
        .order_by(ReportRevision.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("/{report_id}/revisions/{revision_id}/approve", response_model=ReportOut)
async def approve_revision(
    report_id: str,
    revision_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Report:
    report = await db.get(Report, report_id)
    if report is None:
        raise HTTPException(404, "Rapor bulunamadı.")
    revision = await db.get(ReportRevision, revision_id)
    if revision is None or revision.report_id != report_id:
        raise HTTPException(404, "Bu rapora ait bir revizyon bulunamadı.")
    if revision.approved:
        raise HTTPException(409, "Bu revizyon zaten onaylanmış.")

    revision.approved = True
    report.data_snapshot = revision.content

    await record_audit_event(
        db,
        actor=current_user.email,
        action="report_revision.approved",
        project_id=report.project_id,
        details={"report_id": report_id, "revision_id": revision_id},
    )
    await db.commit()
    await db.refresh(report)
    return report


@router.get("/{report_id}/pdf")
async def export_pdf(report_id: str, db: AsyncSession = Depends(get_db)) -> Response:
    report = await db.get(Report, report_id)
    if report is None:
        raise HTTPException(404, "Rapor bulunamadı.")
    try:
        pdf_bytes = await render_report_pdf(report.data_snapshot)
    except PdfRenderError as exc:
        # Sahte/boş bir "başarı" döndürmek yerine gerçek hatayı bildir.
        raise HTTPException(503, f"PDF üretilemedi: {exc}") from exc
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="rapor-{report_id[:8]}.pdf"'},
    )
