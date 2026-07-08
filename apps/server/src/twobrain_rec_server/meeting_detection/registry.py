from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import case, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.admin.audit import write_admin_audit_event
from twobrain_rec_server.db.models import (
    MeetingDetectionNonTargetRule,
    MeetingDetectionReviewAction,
    MeetingTargetRegistryEntry,
    MeetingTargetRegistryVersion,
)
from twobrain_rec_server.meeting_detection.redaction import forbidden_content_findings


class MeetingTargetRegistryError(ValueError):
    """Raised when a meeting target registry document is unsafe or invalid."""


@dataclass(frozen=True, slots=True)
class PublishedRegistryDocument:
    document: dict[str, Any]
    registry_version: str
    etag: str
    registry_version_id: UUID


REGISTRY_VERSION_RE = re.compile(r"^[0-9]{4}\.[0-9]{2}\.[0-9]{2}\.[0-9]+$")
TARGET_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{2,80}$")
BUNDLE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{1,200}$")
WINDOWS_PROCESS_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\- ]{1,200}$")
SAFE_RULE_VALUE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\- ]{1,239}$")
REASON_CODE_RE = re.compile(r"^[a-z0-9][a-z0-9_:-]{1,119}$")

ALLOWED_MODES = {
    "prompt_enabled",
    "diagnostic_only",
    "blocked_missing_bundle",
    "manual_or_browser_only",
    "disabled",
}
ALLOWED_MARKETS = {"global", "russia", "enterprise", "unknown"}
ALLOWED_PLATFORMS = {"macos", "windows", "browser", "cross_platform"}
ALLOWED_TARGET_FAMILIES = {"native_app", "browser_meeting", "provider", "manual_only"}
ALLOWED_EVIDENCE = {
    "runtime_verified",
    "runtime_start_verified",
    "package_verified",
    "installed_verified",
    "confirmed",
    "seed",
    "verify_required",
    "future_windows",
}
ALLOWED_REQUIRED_SIGNALS = {
    "macos_sensor_indicators_mic",
    "browser_metadata",
    "calendar_or_join_intent",
    "windows_future_adapter",
}
ALLOWED_BROWSER_HOST_CATEGORIES = {"first_party", "enterprise_domain", "unknown"}
ALLOWED_BROWSER_PATTERN_CLASSES = {"meeting_room", "join_intent", "landing", "settings", "unsupported"}
ALLOWED_NON_TARGET_RULE_KINDS = {
    "bundle_id",
    "bundle_prefix",
    "display_name_token",
    "category",
    "windows_process_name",
    "browser_service_family",
}
ALLOWED_NON_TARGET_PLATFORMS = {"macos", "windows", "browser"}
PROMPT_EVIDENCE = {"runtime_verified"}
CACHE_CONTROL = "private, max-age=86400"


def load_packaged_seed_registry(seed_path: Path | None = None) -> dict[str, Any]:
    path = seed_path or _packaged_seed_registry_path()
    if not path.exists():
        raise MeetingTargetRegistryError(f"packaged seed registry is missing: {path}")
    return validate_registry_document(json.loads(path.read_text(encoding="utf-8")))


def validate_registry_document(document: dict[str, Any]) -> dict[str, Any]:
    if document.get("schemaVersion") != 1:
        raise MeetingTargetRegistryError("unsupported registry schemaVersion")
    registry_version = str(document.get("registryVersion", ""))
    if not REGISTRY_VERSION_RE.match(registry_version):
        raise MeetingTargetRegistryError("invalid registryVersion")
    targets = document.get("targets")
    if not isinstance(targets, list) or not targets:
        raise MeetingTargetRegistryError("registry requires at least one target")
    seen_ids: set[str] = set()
    for target in targets:
        _validate_target(target, seen_ids=seen_ids)
    _validate_non_target_rules(document.get("nonTargetRules", []))
    return document


def registry_etag(document: dict[str, Any]) -> str:
    canonical = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def registry_entries(document: dict[str, Any]) -> list[dict[str, Any]]:
    validate_registry_document(document)
    entries: list[dict[str, Any]] = []
    for target in document["targets"]:
        entries.append(
            {
                "target_id": target["id"],
                "display_name": target["displayName"],
                "market": target["market"],
                "platform": target["platform"],
                "target_family": target["targetFamily"],
                "mode": target["mode"],
                "evidence": target["evidence"],
                "native_bundle_ids": target.get("nativeBundleIds", []),
                "windows_process_names": target.get("windowsProcessNames", []),
                "browser_service_patterns": target.get("browserServicePatterns", []),
                "required_signals": target["requiredSignals"],
                "comments": target.get("comments"),
            }
        )
    return entries


def registry_version_summary(row: MeetingTargetRegistryVersion) -> dict[str, Any]:
    return {
        "registry_version_id": str(row.id),
        "registry_version": row.registry_version,
        "schema_version": row.schema_version,
        "status": row.status,
        "source": row.source,
        "etag": row.etag,
        "published_at": row.published_at.isoformat() if row.published_at else None,
        "target_count": len((row.document_json or {}).get("targets", [])),
    }


async def get_latest_published_registry(
    db: AsyncSession,
    *,
    workspace_id: UUID,
) -> PublishedRegistryDocument:
    row = await _latest_published_registry_row(db, workspace_id=workspace_id)
    if row is None:
        await seed_packaged_registry_if_missing(db)
        row = await _latest_published_registry_row(db, workspace_id=workspace_id)
    if row is None:
        raise MeetingTargetRegistryError("published registry is unavailable")
    document = await _export_document_with_non_target_rules(
        db,
        row.document_json,
        workspace_id=workspace_id,
    )
    etag = registry_etag(document)
    return PublishedRegistryDocument(
        document=document,
        registry_version=str(document["registryVersion"]),
        etag=etag,
        registry_version_id=row.id,
    )


async def seed_packaged_registry_if_missing(db: AsyncSession) -> MeetingTargetRegistryVersion:
    existing = await db.scalar(
        select(MeetingTargetRegistryVersion).where(
            MeetingTargetRegistryVersion.workspace_id.is_(None),
            MeetingTargetRegistryVersion.status == "published",
        )
    )
    if existing is not None:
        return existing
    document = load_packaged_seed_registry()
    row = MeetingTargetRegistryVersion(
        workspace_id=None,
        registry_version=document["registryVersion"],
        schema_version=document["schemaVersion"],
        status="published",
        source="packaged_seed",
        published_at=datetime.now(UTC),
        document_json=document,
        etag=registry_etag(document),
    )
    db.add(row)
    await db.flush()
    await _replace_registry_entries(db, row=row, document=document)
    return row


async def build_registry_draft_document(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    registry_version: str,
    target: dict[str, Any],
    now: datetime | None = None,
) -> dict[str, Any]:
    base = (await get_latest_published_registry(db, workspace_id=workspace_id)).document
    document = deepcopy(base)
    document["registryVersion"] = registry_version
    document["generatedAt"] = (now or datetime.now(UTC)).isoformat().replace("+00:00", "Z")
    document.pop("expiresAt", None)
    document.pop("nonTargetRules", None)
    targets = [existing for existing in document["targets"] if existing["id"] != target["id"]]
    targets.append(target)
    document["targets"] = targets
    return validate_registry_document(document)


async def publish_registry_draft(
    db: AsyncSession,
    *,
    context: Any,
    draft_id: UUID,
    reason_code: str | None,
) -> dict[str, Any]:
    draft = await db.scalar(
        select(MeetingTargetRegistryVersion).where(
            MeetingTargetRegistryVersion.id == draft_id,
            MeetingTargetRegistryVersion.workspace_id == context.workspace_id,
            MeetingTargetRegistryVersion.status == "draft",
        )
    )
    if draft is None:
        raise MeetingTargetRegistryError("registry draft not found")
    latest = await _latest_workspace_published_registry_row(db, workspace_id=context.workspace_id)
    if (
        latest is not None
        and latest.id != draft.id
        and latest.published_at is not None
        and draft.created_at is not None
        and latest.published_at > draft.created_at
    ):
        raise MeetingTargetRegistryError("registry draft is stale")
    document = validate_registry_document(draft.document_json)
    draft.registry_version = document["registryVersion"]
    draft.schema_version = document["schemaVersion"]
    draft.status = "published"
    draft.published_at = datetime.now(UTC)
    draft.published_by_user_id = context.actor_user_id
    draft.etag = registry_etag(document)
    await _supersede_workspace_registry_versions(db, workspace_id=context.workspace_id, active_id=draft.id)
    await _replace_registry_entries(db, row=draft, document=document)
    action_reason = reason_code or "publish_registry_version"
    db.add(
        MeetingDetectionReviewAction(
            workspace_id=context.workspace_id,
            registry_version_id=draft.id,
            actor_user_id=context.actor_user_id,
            action="publish_registry_version",
            previous_state="draft",
            next_state="published",
            reason_code=action_reason,
            metadata_json={
                "action": "publish_registry_version",
                "reason_code": action_reason,
                "registry_version": draft.registry_version,
            },
        )
    )
    await write_admin_audit_event(
        db,
        workspace_id=context.workspace_id,
        actor_user_id=context.actor_user_id,
        actor_role=context.actor_role,
        action="publish_registry_version",
        target_kind="meeting_detection_registry_version",
        target_id=str(draft.id),
        outcome="completed",
        reason_code=action_reason,
        metadata={
            "action": "publish_registry_version",
            "reason_code": action_reason,
            "target_kind": "meeting_detection_registry_version",
        },
    )
    await db.flush()
    return registry_version_summary(draft)


def _validate_target(target: Any, *, seen_ids: set[str]) -> None:
    if not isinstance(target, dict):
        raise MeetingTargetRegistryError("target must be an object")
    required = ("id", "displayName", "market", "platform", "targetFamily", "mode", "evidence", "requiredSignals")
    missing = [field for field in required if field not in target]
    if missing:
        raise MeetingTargetRegistryError(f"target missing required fields: {','.join(missing)}")
    target_id = str(target["id"])
    if not TARGET_ID_RE.match(target_id):
        raise MeetingTargetRegistryError(f"invalid target id: {target_id}")
    if target_id in seen_ids:
        raise MeetingTargetRegistryError(f"duplicate target id: {target_id}")
    seen_ids.add(target_id)
    if target["market"] not in ALLOWED_MARKETS:
        raise MeetingTargetRegistryError(f"invalid market for {target_id}")
    if target["platform"] not in ALLOWED_PLATFORMS:
        raise MeetingTargetRegistryError(f"invalid platform for {target_id}")
    if target["targetFamily"] not in ALLOWED_TARGET_FAMILIES:
        raise MeetingTargetRegistryError(f"invalid targetFamily for {target_id}")
    if target["mode"] not in ALLOWED_MODES:
        raise MeetingTargetRegistryError(f"invalid mode for {target_id}")
    if target["evidence"] not in ALLOWED_EVIDENCE:
        raise MeetingTargetRegistryError(f"invalid evidence for {target_id}")
    required_signals = target["requiredSignals"]
    if (
        not isinstance(required_signals, list)
        or not required_signals
        or any(signal not in ALLOWED_REQUIRED_SIGNALS for signal in required_signals)
        or len(set(required_signals)) != len(required_signals)
    ):
        raise MeetingTargetRegistryError(f"requiredSignals missing for {target_id}")
    native_bundle_ids = target.get("nativeBundleIds", [])
    if native_bundle_ids and (
        not isinstance(native_bundle_ids, list) or any(not BUNDLE_ID_RE.match(str(bundle_id)) for bundle_id in native_bundle_ids)
    ):
        raise MeetingTargetRegistryError(f"invalid nativeBundleIds for {target_id}")
    if (
        target["platform"] == "macos"
        and target["targetFamily"] == "native_app"
        and target["mode"] == "prompt_enabled"
    ):
        if not native_bundle_ids:
            raise MeetingTargetRegistryError(f"prompt_enabled native target missing nativeBundleIds: {target_id}")
        if target["evidence"] not in PROMPT_EVIDENCE:
            raise MeetingTargetRegistryError(f"prompt_enabled native target lacks runtime evidence: {target_id}")
    if target["targetFamily"] == "browser_meeting":
        signal_set = set(target["requiredSignals"])
        if (
            "browser_metadata" not in signal_set
            or "calendar_or_join_intent" not in signal_set
            or "macos_sensor_indicators_mic" in signal_set
            or not target.get("browserServicePatterns")
        ):
            raise MeetingTargetRegistryError(
                f"browser target requires metadata plus calendar/join intent: {target_id}"
            )
    _validate_browser_patterns(target, target_id=target_id)


def _validate_browser_patterns(target: dict[str, Any], *, target_id: str) -> None:
    patterns = target.get("browserServicePatterns", [])
    if not patterns:
        return
    if not isinstance(patterns, list):
        raise MeetingTargetRegistryError(f"invalid browserServicePatterns for {target_id}")
    for pattern in patterns:
        if not isinstance(pattern, dict):
            raise MeetingTargetRegistryError(f"invalid browserServicePatterns for {target_id}")
        service_family = str(pattern.get("serviceFamily", ""))
        if not TARGET_ID_RE.match(service_family):
            raise MeetingTargetRegistryError(f"invalid browser service family for {target_id}")
        if pattern.get("hostCategory") not in ALLOWED_BROWSER_HOST_CATEGORIES:
            raise MeetingTargetRegistryError(f"invalid browser host category for {target_id}")
        if pattern.get("patternClass") not in ALLOWED_BROWSER_PATTERN_CLASSES:
            raise MeetingTargetRegistryError(f"invalid browser pattern class for {target_id}")


def _validate_non_target_rules(rules: Any) -> None:
    if rules in (None, []):
        return
    if not isinstance(rules, list):
        raise MeetingTargetRegistryError("invalid nonTargetRules")
    seen: set[tuple[str, str, str]] = set()
    for rule in rules:
        if not isinstance(rule, dict):
            raise MeetingTargetRegistryError("invalid nonTargetRules")
        platform = str(rule.get("platform", ""))
        rule_kind = str(rule.get("ruleKind", ""))
        rule_value = str(rule.get("ruleValue", ""))
        reason_code = str(rule.get("reasonCode", ""))
        if platform not in ALLOWED_NON_TARGET_PLATFORMS:
            raise MeetingTargetRegistryError("invalid non-target rule platform")
        if rule_kind not in ALLOWED_NON_TARGET_RULE_KINDS:
            raise MeetingTargetRegistryError("invalid non-target rule kind")
        if rule_kind in {"bundle_id", "bundle_prefix"} and not BUNDLE_ID_RE.match(rule_value):
            raise MeetingTargetRegistryError("invalid non-target bundle rule value")
        if rule_kind == "windows_process_name" and not WINDOWS_PROCESS_RE.match(rule_value):
            raise MeetingTargetRegistryError("invalid non-target process rule value")
        if not SAFE_RULE_VALUE_RE.match(rule_value):
            raise MeetingTargetRegistryError("invalid non-target rule value")
        if forbidden_content_findings(rule_value):
            raise MeetingTargetRegistryError("unsafe non-target rule value")
        if not REASON_CODE_RE.match(reason_code):
            raise MeetingTargetRegistryError("invalid non-target reason code")
        dedupe_key = (platform, rule_kind, rule_value)
        if dedupe_key in seen:
            raise MeetingTargetRegistryError("duplicate non-target rule")
        seen.add(dedupe_key)


async def _latest_published_registry_row(
    db: AsyncSession,
    *,
    workspace_id: UUID,
) -> MeetingTargetRegistryVersion | None:
    scope_rank = case(
        (MeetingTargetRegistryVersion.workspace_id == workspace_id, 0),
        else_=1,
    )
    return await db.scalar(
        select(MeetingTargetRegistryVersion)
        .where(
            MeetingTargetRegistryVersion.status == "published",
            (MeetingTargetRegistryVersion.workspace_id == workspace_id)
            | (MeetingTargetRegistryVersion.workspace_id.is_(None)),
        )
        .order_by(
            scope_rank,
            MeetingTargetRegistryVersion.published_at.desc(),
            MeetingTargetRegistryVersion.created_at.desc(),
        )
        .limit(1)
    )


async def _latest_workspace_published_registry_row(
    db: AsyncSession,
    *,
    workspace_id: UUID,
) -> MeetingTargetRegistryVersion | None:
    return await db.scalar(
        select(MeetingTargetRegistryVersion)
        .where(
            MeetingTargetRegistryVersion.status == "published",
            MeetingTargetRegistryVersion.workspace_id == workspace_id,
        )
        .order_by(
            MeetingTargetRegistryVersion.published_at.desc(),
            MeetingTargetRegistryVersion.created_at.desc(),
        )
        .limit(1)
    )


async def _export_document_with_non_target_rules(
    db: AsyncSession,
    document: dict[str, Any],
    *,
    workspace_id: UUID,
) -> dict[str, Any]:
    exported = deepcopy(document)
    rules = await _active_non_target_rule_entries(db, workspace_id=workspace_id)
    if rules:
        exported["nonTargetRules"] = rules
    else:
        exported["nonTargetRules"] = []
    return validate_registry_document(exported)


async def _active_non_target_rule_entries(
    db: AsyncSession,
    *,
    workspace_id: UUID,
) -> list[dict[str, str]]:
    rows = (
        await db.scalars(
            select(MeetingDetectionNonTargetRule)
            .where(
                MeetingDetectionNonTargetRule.active.is_(True),
                (MeetingDetectionNonTargetRule.workspace_id == workspace_id)
                | (MeetingDetectionNonTargetRule.workspace_id.is_(None)),
            )
            .order_by(
                MeetingDetectionNonTargetRule.platform,
                MeetingDetectionNonTargetRule.rule_kind,
                MeetingDetectionNonTargetRule.rule_value,
            )
        )
    ).all()
    return [
        {
            "platform": row.platform,
            "ruleKind": row.rule_kind,
            "ruleValue": row.rule_value,
            "reasonCode": row.reason_code,
        }
        for row in rows
    ]


async def _replace_registry_entries(
    db: AsyncSession,
    *,
    row: MeetingTargetRegistryVersion,
    document: dict[str, Any],
) -> None:
    await db.execute(
        delete(MeetingTargetRegistryEntry).where(
            MeetingTargetRegistryEntry.registry_version_id == row.id
        )
    )
    await db.flush()
    for entry in registry_entries(document):
        db.add(MeetingTargetRegistryEntry(registry_version_id=row.id, **entry))
    await db.flush()


async def _supersede_workspace_registry_versions(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    active_id: UUID,
) -> None:
    rows = (
        await db.scalars(
            select(MeetingTargetRegistryVersion).where(
                MeetingTargetRegistryVersion.workspace_id == workspace_id,
                MeetingTargetRegistryVersion.status == "published",
                MeetingTargetRegistryVersion.id != active_id,
            )
        )
    ).all()
    for row in rows:
        row.status = "superseded"


def _packaged_seed_registry_path() -> Path:
    for parent in Path(__file__).resolve().parents:
        path = parent / "apps" / "macos" / "RecApp" / "Resources" / "meeting-target-registry.seed.json"
        if path.exists():
            return path
    return Path(__file__).resolve().parents[5] / "apps" / "macos" / "RecApp" / "Resources" / "meeting-target-registry.seed.json"
