from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
FEATURE_DIR = REPO_ROOT / "specs/031-rls-hardening"
FORBIDDEN_EVIDENCE_MARKERS = (
    "raw_transcript_text",
    "raw_audio_bytes",
    "signed_dependency_url",
    "live_secret_path",
    "mediascribe_api_key_value",
)


def test_rls_feature_evidence_uses_placeholder_forbidden_markers_only() -> None:
    checked_files = [
        FEATURE_DIR / "spec.md",
        FEATURE_DIR / "plan.md",
        FEATURE_DIR / "quickstart.md",
        FEATURE_DIR / "contracts/access-outcomes.md",
        FEATURE_DIR / "contracts/tenant-context.md",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in checked_files)

    for marker in FORBIDDEN_EVIDENCE_MARKERS:
        assert marker not in combined
