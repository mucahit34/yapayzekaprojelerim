"""Veri modeli: Project, Asset, Finding, Evidence, Validation, Task,
Conversation, Report, ReportRevision, AuditEvent.

Tasarım kuralları (bkz. README):
- Her Finding/Evidence/Report bir Project'e bağlıdır; proje izolasyonu DB
  seviyesinde zorunlu kılınır (sorgular her zaman project_id ile filtrelenir).
- Bulgu durum makinesi: suspected -> verifying -> confirmed|false_positive;
  confirmed -> remediated_pending_retest -> verifying (yeniden test).
- AuditEvent, her yüksek etkili/aktif test işlemi için zorunlu kayıt alanıdır.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class FindingStatus(str, enum.Enum):
    SUSPECTED = "suspected"
    VERIFYING = "verifying"
    CONFIRMED = "confirmed"
    FALSE_POSITIVE = "false_positive"
    REMEDIATED_PENDING_RETEST = "remediated_pending_retest"


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    AWAITING_APPROVAL = "awaiting_approval"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Yetkili test kapsamı: izinli hedef/alan adları/IP aralıkları ve kapsam
    # dışı öğeler. Aktif test işlemleri bu alana karşı doğrulanmalıdır.
    scope_definition: Mapped[dict] = mapped_column(JSON, default=dict)
    is_archived: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    assets: Mapped[list["Asset"]] = relationship(back_populates="project")
    findings: Mapped[list["Finding"]] = relationship(back_populates="project")
    tasks: Mapped[list["Task"]] = relationship(back_populates="project")
    reports: Mapped[list["Report"]] = relationship(back_populates="project")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="project")


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(50))  # host, domain, url, repo, ...
    identifier: Mapped[str] = mapped_column(String(500))  # ip/domain/url/path
    in_scope: Mapped[bool] = mapped_column(default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    project: Mapped[Project] = relationship(back_populates="assets")
    findings: Mapped[list["Finding"]] = relationship(back_populates="asset")


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    asset_id: Mapped[str | None] = mapped_column(ForeignKey("assets.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[FindingStatus] = mapped_column(
        Enum(FindingStatus), default=FindingStatus.SUSPECTED
    )
    risk_level: Mapped[RiskLevel | None] = mapped_column(Enum(RiskLevel), nullable=True)
    # Uydurma/doğrulanmamış CVE referansı eklenemez; cve_refs yalnızca
    # kanıtla ilişkilendirilmiş, insan/araç tarafından teyit edilmiş girişler
    # içermelidir.
    cve_refs: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    project: Mapped[Project] = relationship(back_populates="findings")
    asset: Mapped[Asset | None] = relationship(back_populates="findings")
    evidence: Mapped[list["Evidence"]] = relationship(back_populates="finding")
    validations: Mapped[list["Validation"]] = relationship(back_populates="finding")


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    finding_id: Mapped[str] = mapped_column(ForeignKey("findings.id"), nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(50))  # screenshot, log, http_tx, ...
    # Ham secret değerleri (parola/anahtar/token) bu alana ASLA yazılmaz;
    # gerekiyorsa maskelenmiş/redacted biçimde saklanır.
    content_ref: Mapped[str] = mapped_column(Text)  # dosya yolu / depolama referansı
    collected_at: Mapped[datetime] = mapped_column(server_default=func.now())

    finding: Mapped[Finding] = relationship(back_populates="evidence")


class Validation(Base):
    __tablename__ = "validations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    finding_id: Mapped[str] = mapped_column(ForeignKey("findings.id"), nullable=False)
    validated_by: Mapped[str] = mapped_column(String(100))  # agent adı veya kullanıcı
    result: Mapped[str] = mapped_column(String(50))  # confirmed, false_positive
    method: Mapped[str] = mapped_column(Text)  # nasıl doğrulandığı
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    finding: Mapped[Finding] = relationship(back_populates="validations")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255))
    agent_role: Mapped[str] = mapped_column(String(100))
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), default=TaskStatus.PENDING)
    # Aktif test / dış hedefe trafik / yüksek riskli işlemler için zorunlu.
    requires_approval: Mapped[bool] = mapped_column(default=True)
    # User.email (255) kadar uzun olabilir — approve_task artık buraya
    # kimlik doğrulanmış kullanıcının e-postasını yazıyor.
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    project: Mapped[Project] = relationship(back_populates="tasks")


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    channel: Mapped[str] = mapped_column(String(20))  # web, telegram
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_pinned: Mapped[bool] = mapped_column(default=False)
    is_archived: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    project: Mapped[Project | None] = relationship(back_populates="conversations")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    template: Mapped[str] = mapped_column(String(100))
    # Rapor üretildiği anda projenin sabitlenmiş veri görüntüsü (snapshot).
    # Rapor, sonradan değişen Finding/Evidence verisinden etkilenmez.
    data_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    project: Mapped[Project] = relationship(back_populates="reports")
    revisions: Mapped[list["ReportRevision"]] = relationship(back_populates="report")


class ReportRevision(Base):
    __tablename__ = "report_revisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    report_id: Mapped[str] = mapped_column(ForeignKey("reports.id"), nullable=False)
    content: Mapped[dict] = mapped_column(JSON, default=dict)  # sayfa/bölüm yapısı
    # AI önerisi mi yoksa kullanıcı tarafından onaylanmış değişiklik mi.
    is_ai_draft: Mapped[bool] = mapped_column(default=False)
    approved: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    report: Mapped[Report] = relationship(back_populates="revisions")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    actor: Mapped[str] = mapped_column(String(100))  # kullanıcı veya agent adı
    action: Mapped[str] = mapped_column(String(255))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
