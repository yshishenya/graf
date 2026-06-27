from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from twobrain_rec_server.observability.redaction import redact_mapping


def metadata_only_calendar_audit(metadata: Mapping[str, Any]) -> dict[str, Any]:
    return redact_mapping(metadata)
