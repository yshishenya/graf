"""Server-only MediaScribe artifact download resolution.

Only allowlisted relative provider paths are persisted. Signed URLs and raw
provider response values never cross the processing or cabinet projection.
"""

from __future__ import annotations

from collections.abc import Mapping
from urllib.parse import unquote, urlsplit

from twobrain_rec_server.mediascribe.schemas import MediaScribeDownloadResponse

DOWNLOAD_ARTIFACTS = frozenset({"archive", "diarization", "summary", "transcript"})


def normalize_download_reference(value: object) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment or parsed.username or parsed.password:
        return None
    path = parsed.path if parsed.path.startswith("/") else f"/{parsed.path}"
    parts = unquote(path).split("/")
    if (
        len(parts) != 7
        or parts[1:4] != ["v1", "audio", "transcriptions"]
        or parts[5] != "downloads"
        or parts[6] not in DOWNLOAD_ARTIFACTS
        or not parts[4]
        or "." in parts[4]
        or ".." in parts[4]
    ):
        return None
    return path


def safe_download_references(values: Mapping[str, object] | None) -> dict[str, str]:
    if not values:
        return {}
    return {
        str(name): normalized
        for name, value in values.items()
        if str(name) in DOWNLOAD_ARTIFACTS
        and (normalized := normalize_download_reference(value)) is not None
    }


def provider_download_path(downloads: Mapping[str, object] | None, artifact: str) -> str | None:
    if artifact not in DOWNLOAD_ARTIFACTS:
        return None
    return safe_download_references(downloads).get(artifact)


async def download_provider_artifact(
    mediascribe_client: object,
    *,
    downloads: Mapping[str, object] | None,
    artifact: str,
    request_id: str | None = None,
) -> MediaScribeDownloadResponse:
    path = provider_download_path(downloads, artifact)
    if path is None:
        raise ValueError("provider_artifact_unavailable")
    downloader = getattr(mediascribe_client, "download_artifact", None)
    if not callable(downloader):
        raise ValueError("provider_download_unavailable")
    return await downloader(path, request_id=request_id)
