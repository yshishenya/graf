"""Private synthetic storage, real maintenance-RLS sessions and SDK read decoder."""

import asyncio
import json
from copy import deepcopy
from datetime import UTC, datetime
from hashlib import sha256
from types import SimpleNamespace
from uuid import UUID

import httpx
from langfuse.api.client import LangfuseAPI
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from twobrain_rec_server.db.session import create_sessionmaker
from twobrain_rec_server.db.tenant_context import (
    MaintenanceTenantContext,
    maintenance_context_settings,
)
from twobrain_rec_server.outcomes.prompt_optimization import optimization_trace_id


class ReceiptStorage:
    def __init__(self, root):
        self.root = root
        self.events = []
        self.before_put = self.after_put = self.after_read = lambda *_: None

    def get_bytes(self, key):
        try:
            value = (self.root / sha256(key.encode()).hexdigest()).read_bytes()
        except FileNotFoundError:
            raise KeyError(key) from None
        self.events.append(("read", key))
        self.after_read(key, value)
        return value

    def put_stream(self, key, stream, length):
        value = stream.read()
        assert len(value) == length
        self.before_put(key, value)
        (self.root / sha256(key.encode()).hexdigest()).write_bytes(value)
        self.events.append(("write", key))
        self.after_put(key, value)

    def replace(self, key, value):
        (self.root / sha256(key.encode()).hexdigest()).write_bytes(value)


def maintenance_factory(owner_sessions):
    owner_engine = owner_sessions.kw["bind"]
    assert owner_engine.url.host in {"127.0.0.1", "localhost", "::1"}
    assert owner_engine.url.database.startswith("twobrain_rec_test_")

    async def setup():
        async with owner_sessions() as db:
            await db.execute(text("""do $$ begin
                if not exists(select 1 from pg_roles where rolname = 'twobrain_rec_maintenance') then
                    create role twobrain_rec_maintenance nologin;
                end if;
            end $$"""))
            await db.execute(text("grant select, insert, update on prompt_optimization_runs, prompt_optimization_call_ledger to twobrain_rec_maintenance"))
            await db.commit()
    asyncio.run(setup())

    def factory(_settings):
        engine = create_async_engine(owner_engine.url, poolclass=NullPool)

        @event.listens_for(engine.sync_engine, "connect")
        def identity(connection, _record):
            cursor = connection.cursor()
            cursor.execute("set session authorization twobrain_rec_maintenance")
            cursor.execute("set row_security = on")
            cursor.close()

        base_sessions = create_sessionmaker(engine)

        def sessions():
            db = base_sessions()
            db.info["tenant_context"] = maintenance_context_settings(MaintenanceTenantContext(
                operation_name="prompt_optimization", actor_id="synthetic-operator",
                reason_category="prompt_optimization", feature_area="prompt_optimization",
            ))
            return db
        return engine, sessions
    return factory


class SyntheticLangfuse:
    """Only synthetic ingestion is faked; confirmation uses the installed SDK."""

    def __init__(self, contract):
        self.snapshots = {item.name: item for item in (
            contract.source, contract.extractor, contract.reflection, *contract.judges.values(),
        )}
        self.sent, self.reads, self.prompt_reads = [], [], []
        self.visible = True
        self.read_status = 200
        self.preflight_error = self.send_error = self.flush_error = None
        self.before_send = self.before_read = lambda: None
        self.mutate_row = lambda row: None
        self.http = httpx.Client(transport=httpx.MockTransport(self._read))
        self.api = LangfuseAPI(base_url="https://synthetic.invalid", httpx_client=self.http)

    def get_prompt(self, name, **kwargs):
        self.prompt_reads.append((name, kwargs))
        if self.preflight_error:
            raise self.preflight_error
        snapshot = self.snapshots[name]
        assert kwargs.get("version", snapshot.version) == snapshot.version
        return SimpleNamespace(version=snapshot.version, prompt=deepcopy(snapshot.prompt),
                               config=deepcopy(snapshot.config))

    def start_observation(self, **kwargs):
        self.before_send()
        self.sent.append(kwargs)
        if self.send_error:
            raise self.send_error
        return SimpleNamespace(end=lambda: None)

    def flush(self):
        if self.flush_error:
            raise self.flush_error

    def _read(self, request):
        self.reads.append(request)
        self.before_read()
        assert request.url.path == "/api/public/v2/observations"
        assert "parseIoAsJson" not in request.url.params
        filters = {row["column"]: row["value"] for row in json.loads(request.url.params["filter"])}
        data = []
        for value in self.sent if self.visible else []:
            metadata = value["metadata"]
            trace_id = optimization_trace_id(UUID(metadata["run_id"]))
            observation_id = sha256(metadata["call_key"].encode()).digest()[:8].hex()
            if filters != {"id": observation_id, "traceId": trace_id}:
                continue
            row = {
                "id": observation_id, "traceId": trace_id, "projectId": "synthetic-project",
                "type": "GENERATION", "startTime": datetime.now(UTC).isoformat(),
                "endTime": datetime.now(UTC).isoformat(), "name": value["name"],
                "input": json.dumps(value["input"]), "output": json.dumps(value["output"]),
                "metadata": deepcopy(metadata), "promptName": metadata["prompt_name"],
                "promptVersion": metadata["prompt_version"], "providedModelName": value["model"],
                "modelParameters": value["model_parameters"],
            }
            self.mutate_row(row)
            data.append(row)
        return httpx.Response(self.read_status, json={"data": data, "meta": {"cursor": None}})
