from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from twobrain_rec_server.db.base import Base


class CalendarSource(Base):
    __tablename__ = "calendar_sources"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    owner_user_id: Mapped[UUID] = mapped_column(ForeignKey("user_identities.id"), nullable=False)
    provider_family: Mapped[str] = mapped_column(String(80), nullable=False)
    provider_label: Mapped[str | None] = mapped_column(String(160))
    auth_mode: Mapped[str] = mapped_column(String(64), nullable=False)
    credential_state: Mapped[str] = mapped_column(String(64), nullable=False, default="pending")
    connection_state: Mapped[str] = mapped_column(String(64), nullable=False, default="active")
    sync_state: Mapped[str] = mapped_column(String(64), nullable=False, default="never_synced")
    sync_horizon_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sync_horizon_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_sync_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_sync_finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_successful_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_safe_error_code: Mapped[str | None] = mapped_column(String(120))
    capabilities_json: Mapped[dict] = mapped_column(JSON, default=dict)
    selected_calendar_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    disconnected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CalendarCredentialEnvelope(Base):
    __tablename__ = "calendar_credential_envelopes"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    calendar_source_id: Mapped[UUID] = mapped_column(ForeignKey("calendar_sources.id"), nullable=False)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    secret_kind: Mapped[str] = mapped_column(String(80), nullable=False)
    sealed_payload: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    key_version: Mapped[str] = mapped_column(String(80), nullable=False)
    secret_fingerprint_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    purged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ExternalCalendar(Base):
    __tablename__ = "external_calendars"
    __table_args__ = (UniqueConstraint("calendar_source_id", "provider_calendar_id"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    calendar_source_id: Mapped[UUID] = mapped_column(ForeignKey("calendar_sources.id"), nullable=False)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    provider_calendar_id: Mapped[str] = mapped_column(String(500), nullable=False)
    display_label: Mapped[str] = mapped_column(String(240), nullable=False)
    owner_email_hash: Mapped[str | None] = mapped_column(String(80))
    owner_display_name: Mapped[str | None] = mapped_column(String(240))
    color: Mapped[str | None] = mapped_column(String(40))
    visibility: Mapped[str] = mapped_column(String(64), nullable=False, default="available")
    sync_token: Mapped[str | None] = mapped_column(String(500))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CalendarEventSnapshot(Base):
    __tablename__ = "calendar_event_snapshots"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    calendar_source_id: Mapped[UUID] = mapped_column(ForeignKey("calendar_sources.id"), nullable=False)
    external_calendar_id: Mapped[UUID] = mapped_column(ForeignKey("external_calendars.id"), nullable=False)
    provider_event_id: Mapped[str | None] = mapped_column(String(500))
    ical_uid: Mapped[str | None] = mapped_column(String(500))
    recurring_series_id: Mapped[str | None] = mapped_column(String(500))
    recurrence_instance_id: Mapped[str | None] = mapped_column(String(500))
    original_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_version: Mapped[str | None] = mapped_column(String(240))
    source_status: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    timezone: Mapped[str | None] = mapped_column(String(80))
    original_start_timezone: Mapped[str | None] = mapped_column(String(80))
    original_end_timezone: Mapped[str | None] = mapped_column(String(80))
    all_day: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    floating_time: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    transparency: Mapped[str | None] = mapped_column(String(64))
    recurrence_rule_json: Mapped[dict | None] = mapped_column(JSON)
    recurrence_exceptions_json: Mapped[list | None] = mapped_column(JSON)
    title: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(String(4000))
    location: Mapped[str | None] = mapped_column(String(1000))
    privacy_class: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown")
    conference_summary_json: Mapped[dict] = mapped_column(JSON, default=dict)
    attachments_metadata_json: Mapped[list] = mapped_column(JSON, default=list)
    provider_extras_json: Mapped[dict] = mapped_column(JSON, default=dict)
    safe_to_show_in_list: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    safe_to_use_as_title: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sensitivity_reasons_json: Mapped[list] = mapped_column(JSON, default=list)
    source_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CalendarParticipant(Base):
    __tablename__ = "calendar_participants"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    calendar_event_snapshot_id: Mapped[UUID] = mapped_column(ForeignKey("calendar_event_snapshots.id"), nullable=False)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    participant_kind: Mapped[str] = mapped_column(String(80), nullable=False)
    response_status: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown")
    email: Mapped[str | None] = mapped_column(String(320))
    email_hash: Mapped[str | None] = mapped_column(String(80))
    display_name: Mapped[str | None] = mapped_column(String(240))
    provider_user_id: Mapped[str | None] = mapped_column(String(240))
    workspace_relation: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown")
    recipient_candidate_class: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ConferenceLinkCandidate(Base):
    __tablename__ = "conference_link_candidates"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    calendar_event_snapshot_id: Mapped[UUID] = mapped_column(ForeignKey("calendar_event_snapshots.id"), nullable=False)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    source_field: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_family: Mapped[str] = mapped_column(String(80), nullable=False)
    url_hash: Mapped[str] = mapped_column(String(80), nullable=False)
    redacted_url_preview: Mapped[str | None] = mapped_column(String(240))
    contains_passcode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sensitivity_class: Mapped[str] = mapped_column(String(80), nullable=False, default="meeting_link")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RecordingCalendarContextLink(Base):
    __tablename__ = "recording_calendar_context_links"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    calendar_event_snapshot_id: Mapped[UUID] = mapped_column(ForeignKey("calendar_event_snapshots.id"), nullable=False)
    context_confidence: Mapped[str] = mapped_column(String(64), nullable=False, default="none")
    context_reasons_json: Mapped[list] = mapped_column(JSON, default=list)
    title_source: Mapped[str] = mapped_column(String(64), nullable=False, default="generic")
    roster_source: Mapped[str] = mapped_column(String(64), nullable=False, default="none")
    manual_override_state: Mapped[str] = mapped_column(String(80), nullable=False, default="none")
    linked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    unlinked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CalendarReminderState(Base):
    __tablename__ = "calendar_reminder_states"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    calendar_event_snapshot_id: Mapped[UUID] = mapped_column(ForeignKey("calendar_event_snapshots.id"), nullable=False)
    device_id: Mapped[UUID] = mapped_column(ForeignKey("registered_devices.id"), nullable=False)
    join_prompt_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    record_prompt_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    join_prompt_state: Mapped[str] = mapped_column(String(64), nullable=False, default="not_due")
    record_prompt_state: Mapped[str] = mapped_column(String(64), nullable=False, default="not_due")
    last_client_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CalendarAuditEvent(Base):
    __tablename__ = "calendar_audit_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    calendar_source_id: Mapped[UUID | None] = mapped_column(ForeignKey("calendar_sources.id"))
    calendar_event_snapshot_id: Mapped[UUID | None] = mapped_column(ForeignKey("calendar_event_snapshots.id"))
    meeting_id: Mapped[UUID | None] = mapped_column(ForeignKey("meetings.id"))
    actor_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("user_identities.id"))
    device_id: Mapped[UUID | None] = mapped_column(ForeignKey("registered_devices.id"))
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    outcome: Mapped[str] = mapped_column(String(64), nullable=False)
    safe_reason_code: Mapped[str | None] = mapped_column(String(120))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
