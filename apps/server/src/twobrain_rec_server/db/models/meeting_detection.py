from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from twobrain_rec_server.db.base import Base


class MeetingTargetRegistryVersion(Base):
    __tablename__ = "meeting_target_registry_versions"
    __table_args__ = (
        Index("ix_meeting_target_registry_versions_workspace_status", "workspace_id", "status"),
        Index("ix_meeting_target_registry_versions_version", "registry_version"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID | None] = mapped_column(ForeignKey("workspaces.id"))
    registry_version: Mapped[str] = mapped_column(String(80), nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="draft")
    source: Mapped[str] = mapped_column(String(80), nullable=False, default="admin")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("user_identities.id"))
    document_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    etag: Mapped[str | None] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MeetingTargetRegistryEntry(Base):
    __tablename__ = "meeting_target_registry_entries"
    __table_args__ = (
        Index("ix_meeting_target_registry_entries_version", "registry_version_id"),
        Index("ix_meeting_target_registry_entries_target", "target_id"),
        Index("ix_meeting_target_registry_entries_mode", "mode"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    registry_version_id: Mapped[UUID] = mapped_column(ForeignKey("meeting_target_registry_versions.id"), nullable=False)
    target_id: Mapped[str] = mapped_column(String(80), nullable=False)
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)
    market: Mapped[str] = mapped_column(String(40), nullable=False)
    platform: Mapped[str] = mapped_column(String(40), nullable=False)
    target_family: Mapped[str] = mapped_column(String(40), nullable=False)
    mode: Mapped[str] = mapped_column(String(40), nullable=False)
    evidence: Mapped[str] = mapped_column(String(80), nullable=False)
    native_bundle_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    windows_process_names: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    browser_service_patterns: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    required_signals: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    comments: Mapped[str | None] = mapped_column(String(500))


class MeetingDetectionTelemetryBatch(Base):
    __tablename__ = "meeting_detection_telemetry_batches"
    __table_args__ = (
        Index("uq_meeting_detection_telemetry_idempotency", "workspace_id", "device_id", "idempotency_key_fingerprint", unique=True),
        Index("ix_meeting_detection_telemetry_workspace_received", "workspace_id", "received_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_identities.id"), nullable=False)
    device_id: Mapped[UUID] = mapped_column(ForeignKey("registered_devices.id"), nullable=False)
    idempotency_key_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    payload_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    client_version: Mapped[str] = mapped_column(String(80), nullable=False)
    platform: Mapped[str] = mapped_column(String(40), nullable=False)
    os_version_major: Mapped[str] = mapped_column(String(40), nullable=False)
    registry_version: Mapped[str] = mapped_column(String(80), nullable=False)
    candidate_filter_version: Mapped[str] = mapped_column(String(80), nullable=False)
    rollup_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    rollup_ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    policy_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    resource_rollup_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    redaction_result: Mapped[str] = mapped_column(String(80), nullable=False, default="accepted")
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MeetingDetectionTargetHealthRollup(Base):
    __tablename__ = "meeting_detection_target_health_rollups"
    __table_args__ = (
        Index("ix_meeting_detection_target_health_workspace_target", "workspace_id", "target_id", "rollup_date"),
        Index("ix_meeting_detection_target_health_registry", "registry_version"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    target_id: Mapped[str] = mapped_column(String(80), nullable=False)
    platform: Mapped[str] = mapped_column(String(40), nullable=False)
    registry_version: Mapped[str] = mapped_column(String(80), nullable=False)
    client_version_bucket: Mapped[str | None] = mapped_column(String(80))
    os_version_major: Mapped[str] = mapped_column(String(40), nullable=False)
    rollup_date: Mapped[date] = mapped_column(Date, nullable=False)
    support_mode: Mapped[str] = mapped_column(String(40), nullable=False)
    signal_families_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    outcomes_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    duration_buckets_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    reason_codes_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)


class MeetingDetectionCandidate(Base):
    __tablename__ = "meeting_detection_candidates"
    __table_args__ = (
        Index("ix_meeting_detection_candidates_workspace_state", "workspace_id", "state"),
        Index("ix_meeting_detection_candidates_bundle", "platform", "bundle_id"),
        Index("uq_meeting_detection_candidates_workspace_bundle", "workspace_id", "platform", "bundle_id", unique=True),
        Index("ix_meeting_detection_candidates_score", "candidate_score"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    platform: Mapped[str] = mapped_column(String(40), nullable=False)
    candidate_kind: Mapped[str] = mapped_column(String(80), nullable=False, default="unknown_native_app")
    state: Mapped[str] = mapped_column(String(60), nullable=False, default="new")
    bundle_id: Mapped[str | None] = mapped_column(String(200))
    display_name: Mapped[str | None] = mapped_column(String(80))
    signing_team_id: Mapped[str | None] = mapped_column(String(20))
    version_samples_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    candidate_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    candidate_reasons_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    suppression_reasons_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    stable_observation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reporting_installation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    manual_record_nearby_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    calendar_or_join_hint_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    first_seen_bucket: Mapped[date | None] = mapped_column(Date)
    last_seen_bucket: Mapped[date | None] = mapped_column(Date)
    proposed_target_id: Mapped[str | None] = mapped_column(String(80))
    merged_target_id: Mapped[str | None] = mapped_column(String(80))
    last_batch_id: Mapped[UUID | None] = mapped_column(ForeignKey("meeting_detection_telemetry_batches.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MeetingDetectionReviewAction(Base):
    __tablename__ = "meeting_detection_review_actions"
    __table_args__ = (
        Index("ix_meeting_detection_review_actions_workspace_created", "workspace_id", "created_at"),
        Index("ix_meeting_detection_review_actions_candidate", "candidate_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    candidate_id: Mapped[UUID | None] = mapped_column(ForeignKey("meeting_detection_candidates.id"))
    registry_version_id: Mapped[UUID | None] = mapped_column(ForeignKey("meeting_target_registry_versions.id"))
    actor_user_id: Mapped[UUID] = mapped_column(ForeignKey("user_identities.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    previous_state: Mapped[str | None] = mapped_column(String(60))
    next_state: Mapped[str | None] = mapped_column(String(60))
    reason_code: Mapped[str | None] = mapped_column(String(120))
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MeetingDetectionNonTargetRule(Base):
    __tablename__ = "meeting_detection_non_target_rules"
    __table_args__ = (
        Index("ix_meeting_detection_non_target_rules_workspace", "workspace_id", "platform", "rule_kind"),
        Index("ix_meeting_detection_non_target_rules_value", "rule_kind", "rule_value"),
        Index(
            "uq_meeting_detection_non_target_rules_workspace_rule",
            "workspace_id",
            "platform",
            "rule_kind",
            "rule_value",
            unique=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID | None] = mapped_column(ForeignKey("workspaces.id"))
    platform: Mapped[str] = mapped_column(String(40), nullable=False)
    rule_kind: Mapped[str] = mapped_column(String(80), nullable=False)
    rule_value: Mapped[str] = mapped_column(String(240), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(120), nullable=False)
    created_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("user_identities.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class MeetingDetectionTelemetryRateLimitBucket(Base):
    __tablename__ = "meeting_detection_telemetry_rate_limit_buckets"
    __table_args__ = (
        Index("uq_meeting_detection_rate_limit_bucket", "workspace_id", "user_id", "device_id", "bucket_key", unique=True),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_identities.id"), nullable=False)
    device_id: Mapped[UUID] = mapped_column(ForeignKey("registered_devices.id"), nullable=False)
    bucket_key: Mapped[str] = mapped_column(String(120), nullable=False)
    window_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    blocked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
