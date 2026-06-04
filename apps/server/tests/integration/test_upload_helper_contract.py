from pathlib import Path

ROOT = Path(__file__).parents[4]


def test_upload_helper_requires_separate_identity_headers() -> None:
    script = (ROOT / "apps/server/scripts/upload_test_artifact.py").read_text(encoding="utf-8")

    assert 'parser.add_argument("--organization", required=True)' in script
    assert 'parser.add_argument("--workspace", required=True)' in script
    assert 'parser.add_argument("--user", required=True)' in script
    assert 'parser.add_argument("--device", required=True)' in script
    assert 'parser.add_argument("--token")' in script
    assert '"X-Organization-Id": args.organization' in script
    assert '"X-Workspace-Id": args.workspace' in script
    assert '"X-User-Id": args.user' in script
    assert '"X-Device-Id": args.device' in script
    assert 'headers["Authorization"] = f"Bearer {args.token}"' in script
    assert 'parser.add_argument("--token", required=True)' not in script
    assert '"expected_tracks": [role for role, _filename in files]' in script
    assert '"expected_track_sizes": expected_track_sizes' in script
    assert 'f"/api/v1/upload-sessions/{session_id}/finalize"' in script
