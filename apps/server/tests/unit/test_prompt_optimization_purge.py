from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

import pytest

from twobrain_rec_server.cli import prompt_optimization as cli_module
from twobrain_rec_server.outcomes.prompt_optimization import (
    OPTIMIZATION_HISTORY_MATERIALIZATION_KEY,
    OPTIMIZATION_HISTORY_MAX_BYTES,
    OPTIMIZATION_HISTORY_STAGING_KEY,
    PromptOptimizationError,
    validate_history_materialization_certificate,
)

RUN_ID = UUID("10000000-0000-0000-0000-000000000001")


def _complete_materialization() -> dict[str, object]:
    return {
        OPTIMIZATION_HISTORY_MATERIALIZATION_KEY: {
            phase: {
                "bytes": 10,
                "chunk_count": 1,
                "snapshot_hash": ("a" if phase == "evolution" else "b") * 64,
                "status": "complete",
            }
            for phase in ("evolution", "heldout")
        },
        OPTIMIZATION_HISTORY_STAGING_KEY: {
            phase: {"status": "started"} for phase in ("evolution", "heldout")
        },
    }


class _DatabaseState:
    def __init__(self, *, budget: dict[str, object]) -> None:
        self.run = SimpleNamespace(status="failed", budget=budget)
        self.ledger_deleted = False


class _Session:
    def __init__(self, state: _DatabaseState) -> None:
        self.state = state
        self.pending_delete = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def get(self, *_args, **_kwargs):
        return self.state.run

    async def execute(self, _statement):
        self.state.ledger_deleted = True

    async def delete(self, _run):
        self.pending_delete = True

    async def commit(self):
        if self.pending_delete:
            self.state.run = None


class _Sessionmaker:
    def __init__(self, state: _DatabaseState) -> None:
        self.state = state

    def __call__(self):
        return _Session(self.state)


@pytest.mark.anyio
async def test_optimizer_purge_keeps_db_authority_after_partial_object_failure_and_retries(
    monkeypatch,
) -> None:
    state = _DatabaseState(budget=_complete_materialization())
    objects = {"prefix/a", "prefix/b", "prefix/c"}
    fail_once = {"prefix/b"}

    class Storage:
        client = SimpleNamespace(
            list_objects=lambda *_args, **_kwargs: [
                SimpleNamespace(object_name=key) for key in sorted(objects)
            ]
        )

        def delete_object(self, key):
            if key in fail_once:
                fail_once.remove(key)
                raise RuntimeError("object store unavailable")
            objects.remove(key)

    monkeypatch.setattr(cli_module, "get_storage", lambda _settings: Storage())
    kwargs = {
        "args": SimpleNamespace(run_id=RUN_ID, confirm=True),
        "settings": SimpleNamespace(minio_bucket="bucket"),
        "sessionmaker": _Sessionmaker(state),
    }

    with pytest.raises(RuntimeError, match="object store unavailable"):
        await cli_module._purge(**kwargs)

    assert state.run is not None
    assert state.ledger_deleted is False
    assert objects == {"prefix/b", "prefix/c"}

    result = await cli_module._purge(**kwargs)

    assert result["status"] == "purged"
    assert result["deleted_object_count"] == 2
    assert state.run is None
    assert state.ledger_deleted is True
    assert objects == set()


@pytest.mark.anyio
async def test_optimizer_purge_retains_staging_when_temporal_materialization_failed(
    monkeypatch,
) -> None:
    state = _DatabaseState(
        budget={
            OPTIMIZATION_HISTORY_MATERIALIZATION_KEY: {
                "evolution": {"status": "complete"},
            },
            OPTIMIZATION_HISTORY_STAGING_KEY: {
                "evolution": {"status": "started"},
                "heldout": {"status": "started"},
            },
        }
    )

    def unexpected_storage(_settings):
        raise AssertionError("incomplete plaintext staging must not be listed or deleted")

    monkeypatch.setattr(cli_module, "get_storage", unexpected_storage)
    result = await cli_module._purge(
        SimpleNamespace(run_id=RUN_ID, confirm=True),
        settings=SimpleNamespace(minio_bucket="bucket"),
        sessionmaker=_Sessionmaker(state),
    )

    assert result == {
        "run_id": str(RUN_ID),
        "status": "blocked_history_materialization",
        "incomplete_phases": ["evolution", "heldout"],
        "staging_plaintext_retained": True,
        "retained_observability": ["langfuse", "temporal_history"],
    }
    assert state.run is not None
    assert state.ledger_deleted is False


@pytest.mark.parametrize(
    "certificate",
    [
        {"status": "complete"},
        {
            "bytes": 10,
            "chunk_count": 1,
            "snapshot_hash": "a" * 64,
            "status": "complete",
            "legacy": True,
        },
        {"bytes": True, "chunk_count": 1, "snapshot_hash": "a" * 64, "status": "complete"},
        {"bytes": 10, "chunk_count": 0, "snapshot_hash": "a" * 64, "status": "complete"},
        {
            "bytes": OPTIMIZATION_HISTORY_MAX_BYTES + 1,
            "chunk_count": 1,
            "snapshot_hash": "a" * 64,
            "status": "complete",
        },
        {"bytes": 10, "chunk_count": 1, "snapshot_hash": "A" * 64, "status": "complete"},
    ],
)
def test_materialization_certificate_rejects_legacy_or_corrupt_shape(certificate) -> None:
    with pytest.raises(PromptOptimizationError, match="materialization_invalid"):
        validate_history_materialization_certificate(certificate, phase="evolution")


def test_materialization_certificate_accepts_only_exact_complete_shape() -> None:
    certificate = _complete_materialization()[OPTIMIZATION_HISTORY_MATERIALIZATION_KEY][
        "evolution"
    ]

    assert validate_history_materialization_certificate(
        certificate,
        phase="evolution",
    ) == certificate


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("staging_certificate", "materialization_certificate"),
    [
        ({"status": "unknown"}, None),
        ({"status": "started", "legacy": True}, None),
        ({"status": "started"}, {"status": "complete"}),
        (
            None,
            {
                "bytes": 10,
                "chunk_count": 1,
                "snapshot_hash": "e" * 64,
                "status": "complete",
            },
        ),
    ],
)
async def test_optimizer_purge_blocks_every_noncanonical_staging_certificate_combination(
    monkeypatch,
    staging_certificate,
    materialization_certificate,
) -> None:
    budget: dict[str, object] = {}
    if staging_certificate is not None:
        budget[OPTIMIZATION_HISTORY_STAGING_KEY] = {"evolution": staging_certificate}
    if materialization_certificate is not None:
        budget[OPTIMIZATION_HISTORY_MATERIALIZATION_KEY] = {
            "evolution": materialization_certificate
        }
    state = _DatabaseState(budget=budget)
    monkeypatch.setattr(
        cli_module,
        "get_storage",
        lambda _settings: (_ for _ in ()).throw(
            AssertionError("noncanonical staging state must block before storage")
        ),
    )

    result = await cli_module._purge(
        SimpleNamespace(run_id=RUN_ID, confirm=True),
        settings=SimpleNamespace(minio_bucket="bucket"),
        sessionmaker=_Sessionmaker(state),
    )

    assert result["status"] == "blocked_history_materialization"
    assert result["incomplete_phases"] == ["evolution"]
    assert state.run is not None


@pytest.mark.anyio
async def test_optimizer_purge_allows_failure_before_plaintext_staging(monkeypatch) -> None:
    state = _DatabaseState(budget={})
    objects = {"prefix/checkpoint"}

    class Storage:
        client = SimpleNamespace(
            list_objects=lambda *_args, **_kwargs: [
                SimpleNamespace(object_name=key) for key in sorted(objects)
            ]
        )

        def delete_object(self, key):
            objects.remove(key)

    monkeypatch.setattr(cli_module, "get_storage", lambda _settings: Storage())
    result = await cli_module._purge(
        SimpleNamespace(run_id=RUN_ID, confirm=True),
        settings=SimpleNamespace(minio_bucket="bucket"),
        sessionmaker=_Sessionmaker(state),
    )

    assert result["status"] == "purged"
    assert result["deleted_object_count"] == 1
    assert state.run is None
    assert state.ledger_deleted is True
    assert objects == set()
