import io
import json
import shutil
import subprocess
import sys
import tarfile
import wave
from hashlib import sha256
from pathlib import Path
from unittest.mock import Mock

import httpx
import pytest

from scripts import create_test_artifact as package
from scripts.upload_test_artifact import JsonHttpClient, upload_package


@pytest.fixture
def artifact(tmp_path):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("real audio generation requires the media runtime's ffmpeg/ffprobe")
    path = tmp_path / "artifact"
    package.create_package(path, 3)
    return path


def archive_bytes(entries):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        for name, data, kind in entries:
            member = tarfile.TarInfo(name)
            member.type = kind
            member.size = len(data)
            if kind in {tarfile.SYMTYPE, tarfile.LNKTYPE}:
                member.linkname = "../sentinel"
            archive.addfile(member, io.BytesIO(data))
    return stream.getvalue()


def package_entries(artifact):
    return [
        (name, (artifact / name).read_bytes(), tarfile.REGTYPE) for name in package.FILES.values()
    ]


def test_package_contains_decodable_canonical_audio(artifact):
    manifest, payloads = package.read_package(artifact)
    assert manifest["schema_version"] == "local-recording-manifest.v5"
    assert set(path.name for path in artifact.iterdir()) == set(package.FILES.values())
    with wave.open(io.BytesIO(payloads["media"])) as audio:
        assert (audio.getnchannels(), audio.getframerate(), audio.getsampwidth()) == (1, 16000, 2)
        assert audio.getnframes() == 3 * 16000
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_streams",
            "-of",
            "json",
            str(artifact / package.FILES["playback"]),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    streams = json.loads(result.stdout)["streams"]
    assert len(streams) == 1
    audio = streams[0]
    assert (audio["codec_name"], audio["profile"], audio["sample_rate"], audio["channels"]) == (
        "aac",
        "LC",
        "48000",
        1,
    )
    assert abs(float(audio["duration"]) - 3) < 0.03
    subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-xerror",
            "-i",
            str(artifact / package.FILES["playback"]),
            "-f",
            "null",
            "-",
        ],
        check=True,
        capture_output=True,
    )


def test_transfer_roundtrip_and_cleanup_without_receiver_ffmpeg(artifact, tmp_path, monkeypatch):
    temporary = tmp_path / "media-tmp"
    temporary.mkdir()
    monkeypatch.setattr(package.tempfile, "tempdir", str(temporary))
    stream = io.BytesIO()
    package.stream_package(stream, 3)
    assert list(temporary.iterdir()) == []
    monkeypatch.setenv("PATH", "")
    target = tmp_path / "received"
    script = Path(package.__file__)
    result = subprocess.run(
        [sys.executable, str(script), "--receive", "--out", str(target)],
        input=stream.getvalue(),
        capture_output=True,
        check=True,
    )
    assert (
        json.loads(result.stdout)["manifest_sha256"]
        == sha256((target / "manifest.json").read_bytes()).hexdigest()
    )
    manifest, payloads = package.read_package(target)
    assert manifest["duration_seconds"] == 3
    assert payloads["media"] == (artifact / package.FILES["media"]).read_bytes()


@pytest.mark.parametrize("duration", [0, -1, 301, None, True])
def test_duration_is_bounded_before_writes(tmp_path, duration):
    target = tmp_path / "output"
    with pytest.raises(ValueError, match="duration"):
        package.create_package(target, duration)
    assert not target.exists()


def test_maximum_duration_fits_transfer_bound(tmp_path):
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg required")
    stream = io.BytesIO()
    package.stream_package(stream, package.MAX_DURATION_SECONDS)
    assert len(stream.getvalue()) < package.MAX_TRANSFER_BYTES
    target = tmp_path / "maximum"
    package.receive_package(io.BytesIO(stream.getvalue()), target)
    manifest, payloads = package.read_package(target)
    assert manifest["duration_seconds"] == package.MAX_DURATION_SECONDS
    assert len(payloads["media"]) == 44 + 32000 * package.MAX_DURATION_SECONDS


@pytest.mark.parametrize("kind", ["directory", "symlink"])
def test_receiver_and_generator_preserve_existing_paths(tmp_path, kind):
    sentinel = tmp_path / "sentinel"
    sentinel.mkdir()
    (sentinel / "keep").write_text("preserve")
    target = tmp_path / "output"
    if kind == "directory":
        target.mkdir()
        (target / "keep").write_text("preserve")
    else:
        target.symlink_to(sentinel, target_is_directory=True)
    for operation in (
        lambda: package.receive_package(io.BytesIO(b""), target),
        lambda: package.create_package(target, 1),
    ):
        with pytest.raises(ValueError, match="new directory"):
            operation()
        assert (target / "keep").read_text() == "preserve"


@pytest.mark.parametrize(
    "name,kind",
    [
        ("../sentinel", tarfile.REGTYPE),
        ("/tmp/sentinel", tarfile.REGTYPE),
        ("extra.txt", tarfile.REGTYPE),
        ("nested/manifest.json", tarfile.REGTYPE),
        ("manifest.json", tarfile.SYMTYPE),
        ("manifest.json", tarfile.LNKTYPE),
        ("manifest.json", tarfile.DIRTYPE),
        ("manifest.json", tarfile.FIFOTYPE),
    ],
)
def test_transfer_rejects_paths_links_and_special_files(tmp_path, name, kind):
    target = tmp_path / "received"
    with pytest.raises(ValueError, match="archive member"):
        package.receive_package(io.BytesIO(archive_bytes([(name, b"{}", kind)])), target)
    assert not target.exists()
    assert not (tmp_path / "sentinel").exists()


@pytest.mark.parametrize(
    "damage",
    [
        "duplicate",
        "missing",
        "checksum",
        "truncated",
        "terminator",
        "oversized",
        "trailing_duplicate",
    ],
)
def test_transfer_rejects_invalid_packages_and_cleans_partial_files(artifact, tmp_path, damage):
    entries = package_entries(artifact)
    if damage == "duplicate":
        entries.append(entries[0])
    elif damage == "missing":
        entries.pop()
    elif damage == "checksum":
        name, data, kind = entries[1]
        entries[1] = (name, data[:-1] + b"x", kind)
    elif damage == "oversized":
        entries[0] = (
            "manifest.json",
            b"x" * (package.FILE_LIMITS["manifest.json"] + 1),
            tarfile.REGTYPE,
        )
    data = archive_bytes(entries)
    if damage == "truncated":
        data = data[:2048]
    elif damage == "terminator":
        data = data[:-1]
    elif damage == "trailing_duplicate":
        data += archive_bytes([entries[0]])
    target = tmp_path / "received"
    with pytest.raises((ValueError, tarfile.TarError)):
        package.receive_package(io.BytesIO(data), target)
    assert not target.exists()


def test_total_transfer_bound_includes_headers_and_padding(artifact, tmp_path, monkeypatch):
    data = archive_bytes(package_entries(artifact))
    monkeypatch.setattr(package, "MAX_TRANSFER_BYTES", len(data) - 1)
    target = tmp_path / "received"
    with pytest.raises(ValueError, match="size limit"):
        package.receive_package(io.BytesIO(data), target)
    assert not target.exists()


@pytest.mark.parametrize("failure", ["encoder", "broken_pipe"])
def test_stream_failure_cleans_producer_directory(tmp_path, monkeypatch, failure):
    monkeypatch.setattr(package.tempfile, "tempdir", str(tmp_path))
    if failure == "encoder":
        monkeypatch.setattr(
            package.subprocess, "run", Mock(side_effect=subprocess.TimeoutExpired("ffmpeg", 90))
        )
        error = subprocess.TimeoutExpired
        stream = io.BytesIO()
    else:
        if not shutil.which("ffmpeg"):
            pytest.skip("ffmpeg required")
        stream = Mock()
        stream.write.side_effect = BrokenPipeError
        error = BrokenPipeError
    with pytest.raises(error):
        package.stream_package(stream, 1)
    assert list(tmp_path.iterdir()) == []


def test_upload_sends_only_v5_and_exact_descriptors(artifact):
    requests = []

    def handle(request):
        requests.append(request)
        assert request.headers["X-Organization-Id"] == "synthetic-org"
        if request.url.path == "/api/v1/meetings":
            payload = json.loads(request.content)
            assert payload["source_kind"] == "initial_mixed_recording"
            assert payload["media_scribe_source_mode"] == "single_wav_v1"
            return httpx.Response(200, json={"meeting_id": "meeting"})
        if request.url.path.endswith("/upload-sessions"):
            payload = json.loads(request.content)
            assert payload["expected_tracks"] == ["manifest", "media", "playback"]
            return httpx.Response(
                200, json={"session_id": "session", "media_revision_id": "revision"}
            )
        if request.method == "PUT":
            assert request.headers["X-Content-SHA256"] == sha256(request.content).hexdigest()
            return httpx.Response(200, json={})
        payload = json.loads(request.content)
        assert [
            (t["track_role"], t["codec"], t["sample_rate_hz"], t["channel_count"])
            for t in payload["tracks"]
        ] == [(role, *package.DESCRIPTORS[role]) for role in package.FILES]
        for track, uploaded in zip(payload["tracks"], requests[2:5], strict=True):
            assert track["byte_length"] == len(uploaded.content)
            assert track["sha256"] == sha256(uploaded.content).hexdigest()
        assert payload["manifest_sha256"] == sha256(requests[2].content).hexdigest()
        return httpx.Response(200, json={"meeting": {"status": "ingested_pending_processing"}})

    result = upload_package(
        JsonHttpClient(
            "http://localhost",
            {"X-Organization-Id": "synthetic-org"},
            transport=httpx.MockTransport(handle),
        ),
        artifact,
    )
    assert result["uploaded_parts"] == 3
    assert result["media_revision_id"] == "revision"
    assert len(requests) == 6


def test_upload_rejects_corruption_before_network(artifact):
    (artifact / package.FILES["media"]).write_bytes(b"invalid")
    client = Mock()
    with pytest.raises(ValueError, match="checksum"):
        upload_package(client, artifact)
    assert not client.mock_calls


def test_upload_stop_after_parts_does_not_finalize(artifact):
    client = Mock()
    client.post_json.side_effect = [{"meeting_id": "meeting"}, {"session_id": "session"}]
    result = upload_package(client, artifact, stop_after_parts=1)
    assert result == {"meeting_id": "meeting", "session_id": "session", "stopped": True}
    assert client.put_bytes.call_count == 1
    assert client.post_json.call_count == 2


def test_upload_never_follows_redirects_or_logs_response_content():
    requests = []

    def handle(request):
        requests.append(request)
        return httpx.Response(
            302, headers={"Location": "https://unapproved.invalid"}, text="private-response"
        )

    client = JsonHttpClient("http://localhost", {}, transport=httpx.MockTransport(handle))
    with pytest.raises(RuntimeError, match="302") as error:
        client.post_json("/test", {})
    assert "private-response" not in str(error.value)
    assert len(requests) == 1
