from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "infra/scripts/publish-appcast-remote.sh"


def run_publish(tmp_path: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    archive = tmp_path / "GRAF-2026.09.20.1.zip"
    archive.write_bytes(b"signed archive")
    appcast = tmp_path / "graf-appcast.xml"
    appcast.write_text(
        """<?xml version=\"1.0\"?>
<rss xmlns:sparkle=\"http://www.andymatuschak.org/xml-namespaces/sparkle\">
  <channel><item>
    <title>2026.09.20.1</title>
    <sparkle:version>2026.09.20.1</sparkle:version>
    <enclosure url=\"https://rec.2brain.pro/static/public/downloads/GRAF-2026.09.20.1.zip\" length="14" />
  </item></channel>
</rss>
""",
        encoding="utf-8",
    )
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
    assert "appcast_publish=dry_run" in result.stdout
    assert "archive_sha256=" in result.stdout
    assert "appcast_sha256=" in result.stdout


def test_publisher_verifies_public_feed_after_remote_install() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "verify_public_feed" in source
    assert "public_feed=pass" in source
    assert "public_archive_length_mismatch" in source
    assert ".graf-appcast-publish.lock" in source
    assert "remote_publication_in_progress" in source


def test_dry_run_rejects_a_feed_length_mismatch(tmp_path: Path) -> None:
    archive = tmp_path / "GRAF-2026.09.20.1.zip"
    archive.write_bytes(b"signed archive")
    appcast = tmp_path / "graf-appcast.xml"
    appcast.write_text(
        '<rss xmlns:sparkle="http://www.andymatuschak.org/xml-namespaces/sparkle">'
        '<item><sparkle:version>2026.09.20.1</sparkle:version>'
        '<enclosure url="https://rec.2brain.pro/static/public/downloads/GRAF-2026.09.20.1.zip" length="1"/>'
        '</item></rss>',
        encoding="utf-8",
    )
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
            "--dry-run",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "appcast enclosure length differs" in result.stderr
