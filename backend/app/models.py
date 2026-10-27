from __future__ import annotations

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.utcnow()


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    MANAGEMENT = "MANAGEMENT"
    RB_OFFICER = "RB_OFFICER"
    PGRC_OFFICER = "PGRC_OFFICER"
    BUREAU_OFFICER = "BUREAU_OFFICER"
    REGIONAL_OFFICER = "REGIONAL_OFFICER"


class CaseStatus(str, enum.Enum):
    PENDING = "PENDING"
    UNDER_PROCESS = "UNDER_PROCESS"
    DISPOSED = "DISPOSED"
    TRANSFERRED = "TRANSFERRED"
    ESCALATED = "ESCALATED"


class CaseCategory(str, enum.Enum):
    FEE = "FEE"
    FACULTY = "FACULTY"
    INFRASTRUCTURE = "INFRASTRUCTURE"
    APPROVAL_VIOLATION = "APPROVAL_VIOLATION"
    ACADEMIC_ADMINISTRATION = "ACADEMIC_ADMINISTRATION"
    RAGGING_DISCRIMINATION = "RAGGING_DISCRIMINATION"
    GOVERNANCE_MISCONDUCT = "GOVERNANCE_MISCONDUCT"
    OTHER = "OTHER"


class SourceType(str, enum.Enum):
    LIVE_PUBLIC = "LIVE_PUBLIC"
    SIMULATOR = "SIMULATOR"
    FILE_UPLOAD = "FILE_UPLOAD"
    MANUAL = "MANUAL"


class OutcomeTag(str, enum.Enum):
    DEFICIENCY_CONFIRMED = "DEFICIENCY_CONFIRMED"
    NO_DEFICIENCY = "NO_DEFICIENCY"
    PENALTY_PROPOSED = "PENALTY_PROPOSED"
    APPROVAL_ACTION_PROPOSED = "APPROVAL_ACTION_PROPOSED"
    CLOSED_NO_ACTION = "CLOSED_NO_ACTION"


class SourceChannel(str, enum.Enum):
    CSS = "CSS"
    CPGRAMS = "CPGRAMS"
    EMAIL = "EMAIL"
    PHYSICAL = "PHYSICAL"
    DIRECT = "DIRECT"
    REGIONAL = "REGIONAL"


class ResolutionStatus(str, enum.Enum):
    RESOLVED = "RESOLVED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    UNRESOLVED = "UNRESOLVED"


class ActionType(str, enum.Enum):
    CREATED = "CREATED"
    STATUS_CHANGED = "STATUS_CHANGED"
    TRANSFERRED = "TRANSFERRED"
    ESCALATED = "ESCALATED"
    REMARK = "REMARK"
    DOCUMENT_ADDED = "DOCUMENT_ADDED"
    LINKED = "LINKED"
    OVERLAP_ACK = "OVERLAP_ACK"
    INSTITUTION_RESOLVED = "INSTITUTION_RESOLVED"
    OUTCOME_TAGGED = "OUTCOME_TAGGED"


class AlertStatus(str, enum.Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    REVIEWED_NO_ACTION = "REVIEWED_NO_ACTION"
    RESOLVED = "RESOLVED"


class LinkType(str, enum.Enum):
    OVERLAP_CROSS_BUREAU = "OVERLAP_CROSS_BUREAU"
    NEAR_DUPLICATE = "NEAR_DUPLICATE"
    CROSS_CHANNEL_DUPLICATE = "CROSS_CHANNEL_DUPLICATE"
    MANUAL = "MANUAL"


class ReviewStatus(str, enum.Enum):
    OPEN = "OPEN"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"


class NotificationType(str, enum.Enum):
    OVERLAP = "OVERLAP"
    PENDING_REMINDER = "PENDING_REMINDER"
    ESCALATION = "ESCALATION"
    SLA = "SLA"


class Bureau(Base):
    __tablename__ = "bureaus"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(180))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    users: Mapped[list[User]] = relationship(back_populates="bureau")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, native_enum=False), index=True)
    bureau_id: Mapped[int | None] = mapped_column(ForeignKey("bureaus.id"), nullable=True, index=True)
    region: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    bureau: Mapped[Bureau | None] = relationship(back_populates="users")


class Institution(Base):
    __tablename__ = "institutions"

    id: Mapped[int] = mapped_column(primary_key=True)
    aicte_permanent_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(300), index=True)
    normalized_name: Mapped[str] = mapped_column(String(300), index=True)
    address: Mapped[str] = mapped_column(Text)
    city: Mapped[str] = mapped_column(String(100), index=True)
    state: Mapped[str] = mapped_column(String(100), index=True)
    region: Mapped[str] = mapped_column(String(80), index=True)
    university_affiliation: Mapped[str | None] = mapped_column(String(250), nullable=True)
    approval_status: Mapped[str] = mapped_column(String(80), default="Approved")
    programme_mix: Mapped[list[Any]] = mapped_column(JSON, default=list)
    aliases: Mapped[list[str]] = mapped_column(JSON, default=list)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    source_type: Mapped[str] = mapped_column(String(30), default=SourceType.SIMULATOR.value, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    alias_rows: Mapped[list[InstitutionAlias]] = relationship(back_populates="institution", cascade="all, delete-orphan")
    cases: Mapped[list[Case]] = relationship(back_populates="institution")


class InstitutionAlias(Base):
    __tablename__ = "institution_aliases"
    __table_args__ = (UniqueConstraint("institution_id", "alias", name="uq_alias_institution"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    institution_id: Mapped[int] = mapped_column(ForeignKey("institutions.id"), index=True)
    alias: Mapped[str] = mapped_column(String(300), index=True)
    source: Mapped[str] = mapped_column(String(30), default="seed")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    institution: Mapped[Institution] = relationship(back_populates="alias_rows")


class Case(Base):
    __tablename__ = "cases"
    __table_args__ = (
        Index("ix_cases_institution_bureau_status", "institution_id", "bureau_id", "status"),
        Index("ix_cases_date_status", "date_received", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    source_channel: Mapped[SourceChannel] = mapped_column(Enum(SourceChannel, native_enum=False), index=True)
    institution_id: Mapped[int | None] = mapped_column(ForeignKey("institutions.id"), nullable=True, index=True)
    raw_institution_text: Mapped[str] = mapped_column(Text)
    subject: Mapped[str | None] = mapped_column(String(240), nullable=True, index=True)
    category: Mapped[CaseCategory] = mapped_column(Enum(CaseCategory, native_enum=False), index=True)
    category_subtype: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    complainant_type: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    narrative: Mapped[str] = mapped_column(Text)
    status: Mapped[CaseStatus] = mapped_column(Enum(CaseStatus, native_enum=False), default=CaseStatus.PENDING, index=True)
    bureau_id: Mapped[int] = mapped_column(ForeignKey("bureaus.id"), index=True)
    assigned_officer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    date_received: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    last_action_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_action_text: Mapped[str] = mapped_column(Text, default="Case created")
    next_action_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_disposal_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolution_status: Mapped[ResolutionStatus] = mapped_column(
        Enum(ResolutionStatus, native_enum=False), default=ResolutionStatus.UNRESOLVED, index=True
    )
    match_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    source_type: Mapped[str] = mapped_column(String(30), default=SourceType.MANUAL.value, index=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    source_name: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    source_record_id: Mapped[str | None] = mapped_column(String(150), nullable=True, index=True)
    raw_payload_id: Mapped[int | None] = mapped_column(ForeignKey("raw_payloads.id"), nullable=True, index=True)
    complainant_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    language: Mapped[str] = mapped_column(String(20), default="en")
    narrative_original: Mapped[str | None] = mapped_column(Text, nullable=True)
    narrative_translated: Mapped[str | None] = mapped_column(Text, nullable=True)
    outcome_tag: Mapped[OutcomeTag | None] = mapped_column(Enum(OutcomeTag, native_enum=False), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    institution: Mapped[Institution | None] = relationship(back_populates="cases")
    bureau: Mapped[Bureau] = relationship()
    assigned_officer: Mapped[User | None] = relationship(foreign_keys=[assigned_officer_id])
    actions: Mapped[list[CaseAction]] = relationship(back_populates="case", order_by="CaseAction.created_at")
    reviews: Mapped[list[ReviewQueue]] = relationship(back_populates="case", cascade="all, delete-orphan")


class CaseAction(Base):
    __tablename__ = "case_actions"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    bureau_id: Mapped[int | None] = mapped_column(ForeignKey("bureaus.id"), nullable=True, index=True)
    action_type: Mapped[ActionType] = mapped_column(Enum(ActionType, native_enum=False), index=True)
    remarks: Mapped[str] = mapped_column(Text, default="")
    document_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    prev_hash: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64), unique=True)

    case: Mapped[Case] = relationship(back_populates="actions")
    actor: Mapped[User | None] = relationship(foreign_keys=[actor_user_id])
    bureau: Mapped[Bureau | None] = relationship()


class CaseLink(Base):
    __tablename__ = "case_links"
    __table_args__ = (UniqueConstraint("case_a_id", "case_b_id", "link_type", name="uq_case_link"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    case_a_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    case_b_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    link_type: Mapped[LinkType] = mapped_column(Enum(LinkType, native_enum=False), index=True)
    similarity_score: Mapped[float] = mapped_column(Float, default=0.0)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class OverlapAlert(Base):
    __tablename__ = "overlap_alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    institution_id: Mapped[int] = mapped_column(ForeignKey("institutions.id"), index=True)
    case_ids: Mapped[list[int]] = mapped_column(JSON, default=list)
    bureaus_involved: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[AlertStatus] = mapped_column(Enum(AlertStatus, native_enum=False), default=AlertStatus.OPEN, index=True)
    acknowledged_by_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    reviewer_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    why_flagged: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    escalated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    institution: Mapped[Institution] = relationship()
    messages: Mapped[list[CoordinationMessage]] = relationship(back_populates="alert", cascade="all, delete-orphan")


class CoordinationMessage(Base):
    __tablename__ = "coordination_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    alert_id: Mapped[int] = mapped_column(ForeignKey("overlap_alerts.id"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    bureau_id: Mapped[int | None] = mapped_column(ForeignKey("bureaus.id"), nullable=True)
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    alert: Mapped[OverlapAlert] = relationship(back_populates="messages")
    author: Mapped[User] = relationship()
    bureau: Mapped[Bureau | None] = relationship()


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[NotificationType] = mapped_column(Enum(NotificationType, native_enum=False), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    user: Mapped[User] = relationship()


class ReviewQueue(Base):
    __tablename__ = "review_queue"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), unique=True, index=True)
    candidate_institutions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    status: Mapped[ReviewStatus] = mapped_column(Enum(ReviewStatus, native_enum=False), default=ReviewStatus.OPEN, index=True)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    chosen_institution_id: Mapped[int | None] = mapped_column(ForeignKey("institutions.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    case: Mapped[Case] = relationship(back_populates="reviews")
    chosen_institution: Mapped[Institution | None] = relationship()



class DataSource(Base):
    __tablename__ = "data_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    kind: Mapped[str] = mapped_column(String(50), index=True)
    mode: Mapped[str] = mapped_column(String(30), default="simulator")
    base_url_masked: Mapped[str | None] = mapped_column(String(300), nullable=True)
    interval_seconds: Mapped[int] = mapped_column(Integer, default=60)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    last_status: Mapped[str] = mapped_column(String(30), default="NEVER")
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    records_total: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms_avg: Mapped[float] = mapped_column(Float, default=0.0)
    source_type: Mapped[str] = mapped_column(String(30), default=SourceType.SIMULATOR.value)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class SyncRun(Base):
    __tablename__ = "sync_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(80), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="RUNNING", index=True)
    fetched: Mapped[int] = mapped_column(Integer, default=0)
    created: Mapped[int] = mapped_column(Integer, default=0)
    duplicates_skipped: Mapped[int] = mapped_column(Integer, default=0)
    auto_linked: Mapped[int] = mapped_column(Integer, default=0)
    sent_to_review: Mapped[int] = mapped_column(Integer, default=0)
    unresolved: Mapped[int] = mapped_column(Integer, default=0)
    errors_json: Mapped[list[Any]] = mapped_column(JSON, default=list)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)


class RawPayload(Base):
    __tablename__ = "raw_payloads"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(80), index=True)
    source_record_id: Mapped[str | None] = mapped_column(String(150), nullable=True, index=True)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    payload_sha256: Mapped[str] = mapped_column(String(64), index=True)
    source_type: Mapped[str] = mapped_column(String(30), default=SourceType.SIMULATOR.value)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class PublicStat(Base):
    __tablename__ = "public_stats"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(80), index=True)
    dataset_key: Mapped[str] = mapped_column(String(100), index=True)
    period: Mapped[str | None] = mapped_column(String(50), nullable=True)
    dimension: Mapped[str | None] = mapped_column(String(100), nullable=True)
    metrics_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    is_snapshot: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class AuditAccessLog(Base):
    __tablename__ = "audit_access_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    resource_type: Mapped[str] = mapped_column(String(50))
    resource_id: Mapped[str] = mapped_column(String(80), index=True)
    reason: Mapped[str] = mapped_column(String(250))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
