from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "infra/scripts/publish-appcast-remote.sh"
VERSION = "2026.09.20.1"


def write_sidecars(archive: Path, appcast: Path, attestation_commit: str = "a" * 40) -> None:
    (archive.parent / f"GRAF-{VERSION}.sha256").write_text(
        "{}  {}\n{}  {}\n".format(
            hashlib.sha256(archive.read_bytes()).hexdigest(),
            archive.name,
            hashlib.sha256(appcast.read_bytes()).hexdigest(),
            appcast.name,
        ),
        encoding="utf-8",
    )
    (archive.parent / f"GRAF-{VERSION}-signing-attestation.json").write_text(
        json.dumps({"releaseRef": f"v{VERSION}", "commit": attestation_commit}),
        encoding="utf-8",
    )


def run_publish(
    tmp_path: Path, *extra: str, attestation_commit: str = "a" * 40
) -> subprocess.CompletedProcess[str]:
    archive = tmp_path / "GRAF-2026.09.20.1.zip"
    archive.write_bytes(b"signed archive")
    appcast = tmp_path / "graf-appcast.xml"
    appcast.write_text(
        """<?xml version=\"1.0\"?>
<rss xmlns:sparkle=\"http://www.andymatuschak.org/xml-namespaces/sparkle\">
  <channel><item>
    <title>2026.09.20.1</title>
    <sparkle:version>2026.09.20.1</sparkle:version>
    <enclosure sparkle:edSignature=\"fixture-signature\" url=\"https://rec.2brain.pro/static/public/downloads/GRAF-2026.09.20.1.zip\" length="14" />
  </item></channel>
</rss>
""",
        encoding="utf-8",
    )
    write_sidecars(archive, appcast, attestation_commit)
    return subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--version",
            "2026.09.20.1",
            "--archive",
            str(archive),
            "--appcast",
            str(appcast),
            "--source-sha",
            "a" * 40,
            "--dry-run",
            *extra,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_dry_run_validates_signed_archive_and_feed_binding(tmp_path: Path) -> None:
    result = run_publish(tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "appcast_local_validation=pass" in result.stdout
    assert "appcast_artifact_binding=pass" in result.stdout
    assert "appcast_publish=dry_run" in result.stdout
    assert "archive_sha256=" in result.stdout
    assert "appcast_sha256=" in result.stdout


def test_publisher_verifies_public_feed_after_remote_install() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "verify_public_feed" in source
    assert "public_feed=pass" in source
    assert "public_archive_length_mismatch" in source
    assert "public_appcast_signature_mismatch" in source
    assert "public_archive_sha256_mismatch" in source
    assert "signing_attestation" in source
    assert "source_sha_required" in source
    assert "release checksum does not match prepared bytes" in source
    assert '[[ "$live_signature" == "$local_appcast_signature" ]]' in source
    assert '[[ "$live_archive_sha" == "$archive_sha" ]]' in source
    assert ".graf-appcast-publish.lock" in source
    assert "remote_publication_in_progress" in source
    assert "appcast_publish=rolled_back" in source
    assert ".graf-appcast-transaction-" in source
    assert "kill -0" in source


def test_remote_transaction_journal_is_durable_before_each_swap() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "recover_stale_transactions()" in source
    assert "rollback_transaction_file()" in source
    assert "archive_name=%s" in source
    assert source.index("recover_stale_transactions\nwrite_transaction") < source.index(
        'if [[ -e "$archive_target" ]]'
    )
    assert source.index('archive_installed=1\n  write_transaction\n  mv -- "$archive_temporary"') < source.index(
        'mv -- "$archive_temporary" "$archive_target"'
    )
    assert source.index('appcast_updated=1\nwrite_transaction\nmv -- "$appcast_temporary"') < source.index(
        'mv -- "$appcast_temporary" "$appcast_target"'
    )


def test_dry_run_rejects_a_feed_length_mismatch(tmp_path: Path) -> None:
    archive = tmp_path / "GRAF-2026.09.20.1.zip"
    archive.write_bytes(b"signed archive")
    appcast = tmp_path / "graf-appcast.xml"
    appcast.write_text(
        '<rss xmlns:sparkle="http://www.andymatuschak.org/xml-namespaces/sparkle">'
        '<item><sparkle:version>2026.09.20.1</sparkle:version>'
        '<enclosure sparkle:edSignature="fixture-signature" '
        'url="https://rec.2brain.pro/static/public/downloads/GRAF-2026.09.20.1.zip" length="1"/>'
        '</item></rss>',
        encoding="utf-8",
    )
    write_sidecars(archive, appcast)
    result = subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--version",
            "2026.09.20.1",
            "--archive",
            str(archive),
            "--appcast",
            str(appcast),
            "--source-sha",
            "a" * 40,
            "--dry-run",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "appcast enclosure length differs" in result.stderr


def test_dry_run_rejects_an_unapproved_remote_path(tmp_path: Path) -> None:
    result = run_publish(tmp_path, "--remote-path", "/tmp/infra/runtime/public-downloads")

    assert result.returncode != 0
    assert "remote_path_not_allowed" in result.stderr


def test_dry_run_rejects_an_unsafe_remote_host(tmp_path: Path) -> None:
    result = run_publish(tmp_path, "--host", "-oProxyCommand=touch /tmp/pwned")

    assert result.returncode != 0
    assert "remote_host_invalid" in result.stderr


def test_dry_run_requires_the_exact_public_archive_path(tmp_path: Path) -> None:
    archive = tmp_path / "GRAF-2026.09.20.1.zip"
    archive.write_bytes(b"signed archive")
    appcast = tmp_path / "graf-appcast.xml"
    appcast.write_text(
        '<rss xmlns:sparkle="http://www.andymatuschak.org/xml-namespaces/sparkle">'
        '<item><sparkle:version>2026.09.20.1</sparkle:version>'
        '<enclosure sparkle:edSignature="fixture-signature" '
        'url="https://rec.2brain.pro/static/other/GRAF-2026.09.20.1.zip" length="14"/>'
        '</item></rss>',
        encoding="utf-8",
    )
    write_sidecars(archive, appcast)
    result = subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--version",
            "2026.09.20.1",
            "--archive",
            str(archive),
            "--appcast",
            str(appcast),
            "--source-sha",
            "a" * 40,
            "--dry-run",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "expected HTTPS public archive" in result.stderr


def test_dry_run_rejects_an_attestation_for_another_source(tmp_path: Path) -> None:
    result = run_publish(tmp_path, attestation_commit="b" * 40)

    assert result.returncode != 0
    assert "attestation commit does not match source SHA" in result.stderr
