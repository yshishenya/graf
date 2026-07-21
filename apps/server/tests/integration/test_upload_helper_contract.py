from pathlib import Path

ROOT = Path(__file__).parents[4]


def test_upload_helper_requires_separate_identity_headers() -> None:
    script = (ROOT / "apps/server/scripts/upload_test_artifact.py").read_text(encoding="utf-8")

    assert 'parser.add_argument("--organization", required=True)' in script
    assert 'parser.add_argument("--workspace", required=True)' in script
    assert 'parser.add_argument("--user", required=True)' in script
    assert 'parser.add_argument("--device", required=True)' in script
    assert 'parser.add_argument("--token", help=argparse.SUPPRESS)' in script
    assert 'parser.add_argument("--token-file", type=Path)' in script
    assert 'parser.add_argument("--run-id")' in script
    assert "if args.token and args.token_file:" in script
    assert 'parser.error("--token is not supported; use --token-file")' in script
    assert "read_private_auth_material(args.token_file, expected_run_id=args.run_id)" in script
    assert "validate_origin(args.api)" in script
    assert '"X-Organization-Id": args.organization' in script
    assert '"X-Workspace-Id": args.workspace' in script
    assert '"X-User-Id": args.user' in script
    assert '"X-Device-Id": args.device' in script
    assert 'headers["Authorization"] = f"Bearer {bearer_token}"' in script
    assert 'parser.add_argument("--token", required=True)' not in script
    assert '"expected_tracks": [role for role, _filename in files]' in script
    assert '"expected_track_sizes": expected_track_sizes' in script
    assert 'f"/api/v1/upload-sessions/{session_id}/finalize"' in script
