from __future__ import annotations

import re

SUPPORTED_MEDIA_FILENAME_EXTENSIONS = (
    "wav",
    "wave",
    "rf64",
    "w64",
    "mp3",
    "aac",
    "adts",
    "flac",
    "ogg",
    "oga",
    "opus",
    "m4a",
    "mp4",
    "mov",
    "m4v",
    "webm",
    "mkv",
    "mka",
)
# Keep the pre-Feature-122 serialized title contract stable for API clients.
# Browser presentation may clean every supported upload extension, while the
# public list/detail payloads continue to clean only this historical set.
LEGACY_SERIALIZED_MEDIA_FILENAME_EXTENSIONS = (
    "wav",
    "mp3",
    "m4a",
    "aac",
    "flac",
    "ogg",
    "mp4",
    "mov",
    "m4v",
    "webm",
    "mkv",
)
SUPPORTED_MEDIA_MIME_TYPES = (
    "audio/wav",
    "audio/x-wav",
    "audio/vnd.wave",
    "audio/mpeg",
    "audio/aac",
    "audio/flac",
    "audio/ogg",
    "video/ogg",
    "audio/mp4",
    "video/mp4",
    "video/quicktime",
    "audio/webm",
    "video/webm",
    "audio/x-matroska",
    "video/x-matroska",
)
MANUAL_MEDIA_UPLOAD_ACCEPT = ",".join(
    tuple(f".{extension}" for extension in SUPPORTED_MEDIA_FILENAME_EXTENSIONS)
    + SUPPORTED_MEDIA_MIME_TYPES
)
MEDIA_FILENAME_EXTENSION_ALTERNATION = "|".join(SUPPORTED_MEDIA_FILENAME_EXTENSIONS)
MEDIA_FILENAME_EXTENSION_PATTERN = rf"\.(?:{MEDIA_FILENAME_EXTENSION_ALTERNATION})$"
MEDIA_FILENAME_EXTENSION_RE = re.compile(MEDIA_FILENAME_EXTENSION_PATTERN, re.IGNORECASE)
LEGACY_SERIALIZED_MEDIA_FILENAME_EXTENSION_RE = re.compile(
    rf"\.(?:{'|'.join(LEGACY_SERIALIZED_MEDIA_FILENAME_EXTENSIONS)})$",
    re.IGNORECASE,
)


def media_filename_leaf(value: str) -> str:
    return re.split(r"[/\\]", value)[-1].strip()


def clean_media_filename_title(value: str) -> str:
    leaf = media_filename_leaf(value)
    without_extension = MEDIA_FILENAME_EXTENSION_RE.sub("", leaf)
    normalized = re.sub(r"_+", " ", without_extension)
    return re.sub(r"\s+", " ", normalized).strip()


def clean_legacy_serialized_media_filename_title(value: str) -> str:
    leaf = media_filename_leaf(value)
    without_extension = LEGACY_SERIALIZED_MEDIA_FILENAME_EXTENSION_RE.sub("", leaf)
    normalized = re.sub(r"_+", " ", without_extension)
    return re.sub(r"\s+", " ", normalized).strip()
