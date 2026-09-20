from __future__ import annotations

import time
from pathlib import Path

from twobrain_rec_server.product_analytics.access_governance import (
    BLOCKER_ACCEPTED_OPERATORS_BELOW_MINIMUM,
    BLOCKER_ACCESS_STATE_INVALID,
    BLOCKER_ACCESS_STATE_STALE,
    BLOCKER_ACCESS_STATE_UNAVAILABLE,
    BLOCKER_AUDIT_REVIEW_MISSING,
    BLOCKER_DIGEST_MISMATCH,
    BLOCKER_MFA_OPERATORS_BELOW_MINIMUM,
    BLOCKER_REVOCATION_REVIEW_MISSING,
    BLOCKER_ROTATION_REVIEW_MISSING,
    access_governance_blockers,
    read_access_governance_state,
)


def _write_state(
    directory: Path,
    *,
    now: int,
    accepted: int = 2,
    mfa: int = 2,
    expires_at: int | None = None,
    digest: str = "sha256:" + "a" * 64,
    config_digest: str | None = None,
    installed_digest: str | None = None,
    revocation: str = "complete",
    rotation: str = "complete",
    audit: str = "complete",
    extra: str = "",
) -> Path:
    path = directory / "access-governance-state"
    config_digest = config_digest or digest
    installed_digest = installed_digest or digest
    lines = [
        "access_governance_state_version=1",
        f"reviewed_at={now - 60}",
        f"expires_at={expires_at if expires_at is not None else now + 86400}",
        f"accepted_operator_count={accepted}",
        f"mfa_operator_count={mfa}",
        f"repository_digest={digest}",
        f"config_digest={config_digest}",
        f"installed_guard_digest={installed_digest}",
        f"revocation_review={revocation}",
        f"credential_rotation_review={rotation}",
        f"audit_review={audit}",
    ]
    if extra:
        lines.append(extra)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _env(path: Path) -> dict[str, str]:
    return {"GRAF_PRODUCT_ANALYTICS_ACCESS_GOVERNANCE_STATE_FILE": str(path)}


def test_missing_state_fails_closed() -> None:
    evidence = read_access_governance_state(
        {"GRAF_PRODUCT_ANALYTICS_ACCESS_GOVERNANCE_STATE_FILE": "/no/such/state"}
    )
    assert BLOCKER_ACCESS_STATE_UNAVAILABLE in access_governance_blockers(evidence, now=1)


def test_valid_metadata_state_requires_two_operators_with_mfa(tmp_path: Path) -> None:
    now = int(time.time())
    path = _write_state(tmp_path, now=now)
    evidence = read_access_governance_state(_env(path))
    assert evidence.state_valid is True
    assert access_governance_blockers(evidence, environ=_env(path), now=now) == ()


def test_stale_state_and_operator_minimums_block(tmp_path: Path) -> None:
    now = int(time.time())
    path = _write_state(tmp_path, now=now, accepted=1, mfa=1, expires_at=now - 1)
    blockers = access_governance_blockers(
        read_access_governance_state(_env(path)), environ=_env(path), now=now
    )
    assert BLOCKER_ACCESS_STATE_STALE in blockers
    assert BLOCKER_ACCEPTED_OPERATORS_BELOW_MINIMUM in blockers
    assert BLOCKER_MFA_OPERATORS_BELOW_MINIMUM in blockers


def test_digest_mismatch_and_missing_reviews_block(tmp_path: Path) -> None:
    now = int(time.time())
    path = _write_state(
        tmp_path,
        now=now,
        config_digest="sha256:" + "b" * 64,
        rotation="pending",
        revocation="pending",
        audit="pending",
    )
    blockers = access_governance_blockers(
        read_access_governance_state(_env(path)), environ=_env(path), now=now
    )
    assert BLOCKER_DIGEST_MISMATCH in blockers
    assert BLOCKER_REVOCATION_REVIEW_MISSING in blockers
    assert BLOCKER_ROTATION_REVIEW_MISSING in blockers
    assert BLOCKER_AUDIT_REVIEW_MISSING in blockers


def test_invalid_or_forbidden_state_is_rejected(tmp_path: Path) -> None:
    now = int(time.time())
    path = _write_state(tmp_path, now=now, extra="operator_email=operator@example.test")
    evidence = read_access_governance_state(_env(path))
    assert BLOCKER_ACCESS_STATE_INVALID in access_governance_blockers(evidence, now=now)
