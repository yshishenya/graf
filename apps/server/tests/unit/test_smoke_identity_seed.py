from uuid import UUID

import pytest

from twobrain_rec_server.config import LOCAL_DEV_SMOKE_IDS
from twobrain_rec_server.deployment import SmokeIdentitySeed, build_smoke_identity_seed


def test_build_smoke_identity_seed_is_stable_and_not_local_dev_seed() -> None:
    first = build_smoke_identity_seed("smoke-20260604-0001")
    second = build_smoke_identity_seed("smoke-20260604-0001")

    assert first == second
    assert set(first.headers().values()).isdisjoint({str(identifier) for identifier in LOCAL_DEV_SMOKE_IDS})


def test_smoke_identity_seed_rejects_local_development_identifiers() -> None:
    local = UUID("10000000-0000-0000-0000-000000000001")

    with pytest.raises(ValueError, match="local development"):
        SmokeIdentitySeed(
            organization_id=local,
            workspace_id=UUID("21000000-0000-0000-0000-000000000001"),
            user_id=UUID("31000000-0000-0000-0000-000000000001"),
            device_id=UUID("41000000-0000-0000-0000-000000000001"),
        )


def test_smoke_identity_seed_headers_match_ingest_contract() -> None:
    seed = build_smoke_identity_seed("smoke-20260604-0002")

    assert set(seed.headers()) == {
        "X-Organization-Id",
        "X-Workspace-Id",
        "X-User-Id",
        "X-Device-Id",
    }
