import asyncio
import json
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import twobrain_rec_server.ingest.store as store_module
from tests.fakes.auth_contexts import (
    AUTH_BOOTSTRAP_WORKSPACE_ID,
    DEVICE_ID,
    ORG_ID,
    PERSONAL_WORKSPACE_ID,
    REVOKED_DEVICE_ID,
    USER_ID,
    WORKSPACE_ID,
)
from tests.fakes.fake_minio import FakeMinioStorage
from tests.fixtures.postgres_test_database import (
    ensure_disposable_media_role,
    prepare_schema,
    reset_mapped_tables,
)
from twobrain_rec_server.cabinet import user_time as user_time_module
from twobrain_rec_server.calendar.providers import (
    CalendarCatalogEntry,
    CalendarEventPage,
    CalendarValidation,
)
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import (
    MeetingTargetRegistryEntry,
    MeetingTargetRegistryVersion,
    Organization,
    RegisteredDevice,
    UserIdentity,
    Workspace,
    WorkspaceMembership,
)
from twobrain_rec_server.ingest.store import InMemoryIngestStore
from twobrain_rec_server.main import create_app
from twobrain_rec_server.meeting_detection.registry import registry_entries, registry_etag
from twobrain_rec_server.observability import langfuse as langfuse_module

pytest_plugins = (
    "tests.fixtures.cabinet_exports",
    "tests.fixtures.postgres_test_database",
    "tests.fixtures.postgres_rls",
    "tests.fixtures.test_resources",
)

REGISTRY_DATA = (
    Path(__file__).resolve().parents[1]
    / "src/twobrain_rec_server/db/migrations/data/0030_meeting_target_registry.json"
)
REGISTRY_DOCUMENT = json.loads(REGISTRY_DATA.read_text(encoding="utf-8"))

_MISSING = object()

# Request-scoped context that must not survive from one test to the next once a
# single application instance is shared by the whole worker process.
_REQUEST_CONTEXT_DEFAULTS = (
    (user_time_module._display_timezone, "UTC"),
    (user_time_module._device_timezone, "UTC"),
    (user_time_module._viewer_time, None),
    (user_time_module._reload_allowed, False),
    (langfuse_module._forced_trace_id, None),
    (langfuse_module._forced_span_ids, ()),
)


class SyntheticCalendarConnectionProvider:
    """Metadata-only provider double for routes that must validate before persistence."""

    def __init__(self, provider_family: str) -> None:
        self.provider_family = provider_family
        self.catalog = tuple(
            CalendarCatalogEntry(
                provider_calendar_id=calendar_id,
                display_label=f"Synthetic {calendar_id} calendar",
                primary=calendar_id == "primary",
            )
            for calendar_id in ("primary", "secondary", "team", "selected", "synthetic-primary")
        )

    async def validate(self, credential: str) -> CalendarValidation:
        assert credential
        return CalendarValidation(
            account_subject="sha256:synthetic-account",
            account_label="Synthetic calendar account",
            calendars=self.catalog,
        )

    async def list_calendars(self, credential: str, *, page_token: str | None = None):
        return self.catalog, None

    async def list_events(
        self,
        credential: str,
        *,
        calendar_id: str,
        time_min=None,
        time_max=None,
        page_token: str | None = None,
        sync_token: str | None = None,
    ) -> CalendarEventPage:
        return CalendarEventPage()


async def _seed_database(database_url: str) -> None:
    seed_engine = create_async_engine(database_url, poolclass=NullPool)
    seed_sessionmaker = async_sessionmaker(seed_engine, expire_on_commit=False)
    try:
        async with seed_sessionmaker() as session:
            registry_version = MeetingTargetRegistryVersion(
                workspace_id=None,
                registry_version=REGISTRY_DOCUMENT["registryVersion"],
                schema_version=REGISTRY_DOCUMENT["schemaVersion"],
                status="published",
                source="migration",
                document_json=REGISTRY_DOCUMENT,
                etag=registry_etag(REGISTRY_DOCUMENT),
            )
            session.add_all(
                [
                    Organization(id=ORG_ID, slug="test-org", name="Test Org"),
                    Workspace(
                        id=AUTH_BOOTSTRAP_WORKSPACE_ID,
                        organization_id=ORG_ID,
                        slug="test-auth-bootstrap",
                        name="Test Auth Bootstrap",
                        kind="corporate",
                    ),
                    Workspace(
                        id=WORKSPACE_ID,
                        organization_id=ORG_ID,
                        slug="test-workspace",
                        name="Test Workspace",
                        kind="corporate",
                    ),
                    Workspace(
                        id=PERSONAL_WORKSPACE_ID,
                        organization_id=ORG_ID,
                        owner_user_id=USER_ID,
                        slug=f"personal-{USER_ID.hex}",
                        name="Моё пространство",
                        kind="personal",
                    ),
                    UserIdentity(
                        id=USER_ID,
                        organization_id=ORG_ID,
                        external_subject=str(USER_ID),
                        display_name="Test User",
                    ),
                    registry_version,
                ]
            )
            await session.flush()
            session.add_all(
                [
                    WorkspaceMembership(
                        workspace_id=WORKSPACE_ID,
                        user_id=USER_ID,
                        role="owner",
                        status="active",
                    ),
                    WorkspaceMembership(
                        workspace_id=PERSONAL_WORKSPACE_ID,
                        user_id=USER_ID,
                        role="owner",
                        status="active",
                    ),
                    RegisteredDevice(
                        id=DEVICE_ID,
                        workspace_id=WORKSPACE_ID,
                        user_id=USER_ID,
                        device_public_id="test-device",
                        status="active",
                    ),
                    RegisteredDevice(
                        id=REVOKED_DEVICE_ID,
                        workspace_id=WORKSPACE_ID,
                        user_id=USER_ID,
                        device_public_id="revoked-device",
                        status="revoked",
                    ),
                ]
            )
            session.add_all(
                MeetingTargetRegistryEntry(
                    registry_version_id=registry_version.id,
                    **entry,
                )
                for entry in registry_entries(REGISTRY_DOCUMENT)
            )
            await session.commit()
    finally:
        await seed_engine.dispose()


@pytest.fixture(scope="session")
def postgres_schema_database_url(postgres_worker_database_url: str) -> str:
    prepare_schema(postgres_worker_database_url)
    return postgres_worker_database_url


@pytest.fixture(scope="session")
def postgres_media_database_url(postgres_schema_database_url: str) -> str:
    return asyncio.run(ensure_disposable_media_role(postgres_schema_database_url))


@pytest.fixture
def postgres_seeded_database_url(postgres_schema_database_url: str) -> str:
    asyncio.run(reset_mapped_tables(postgres_schema_database_url))
    asyncio.run(_seed_database(postgres_schema_database_url))
    return postgres_schema_database_url


@pytest.fixture
def test_settings(postgres_seeded_database_url: str) -> Settings:
    return Settings(
        database_url=postgres_seeded_database_url,
        minio_endpoint="localhost:9000",
        minio_access_key="test",
        minio_secret_key="test",
        minio_bucket="test-bucket",
        web_login_workspace_id=AUTH_BOOTSTRAP_WORKSPACE_ID,
    )


class _SessionScopedApplication:
    """One application instance reused by every test in a worker process.

    Building the application is cheap after the first time, but the FIRST request
    to each route is not: FastAPI assembles that route's request/response schema
    lazily, which costs about one second per route. That cost is bound to the
    application instance and is paid again for every new instance, so creating
    the application per test made the whole suite pay it thousands of times.

    Isolation between tests is unchanged: the database is still truncated and
    re-seeded for every test (``postgres_seeded_database_url``). Only the
    application object, its engines and its storage are shared.
    """

    def __init__(self, settings: Settings, media_database_url: str) -> None:
        self.engine = create_async_engine(settings.database_url, poolclass=NullPool)
        self.sessionmaker = async_sessionmaker(self.engine, expire_on_commit=False)
        self.media_engine = create_async_engine(media_database_url, poolclass=NullPool)
        self.media_sessionmaker = async_sessionmaker(self.media_engine, expire_on_commit=False)
        self.storage = FakeMinioStorage()
        with (
            patch("twobrain_rec_server.main.create_engine", return_value=self.engine),
            patch("twobrain_rec_server.main.create_sessionmaker", return_value=self.sessionmaker),
            patch("twobrain_rec_server.main.get_storage", return_value=self.storage),
        ):
            self.app = create_app(settings)
        self.app.state.calendar_provider_factory = SyntheticCalendarConnectionProvider
        self._client: TestClient | None = None
        self._settings_snapshot = dict(settings.__dict__)
        # Application state keeps lazily attached collaborators (temporal client,
        # calendar provider, ingest store) and tests also remove or replace
        # startup names such as the sessionmaker. Remember the whole startup
        # mapping so any added, replaced or deleted name is restored.
        self._state_snapshot = dict(self._state_mapping())

    def _state_mapping(self) -> dict[str, object]:
        """Return the live backing mapping of ``app.state``.

        Starlette keeps application state in ``State._state``; older or wrapped
        versions may expose it directly, so both shapes are handled.
        """
        state = self.app.state
        backing = getattr(state, "_state", None)
        if isinstance(backing, dict):
            return backing
        return {key: value for key, value in vars(state).items()}

    def restore_settings(self) -> None:
        """Undo state a test changed on the shared application.

        The application object lives for the whole worker process, and many
        tests adjust ``client.app.state`` in place (settings such as production
        mode or ``web_login_workspace_id``, plus lazily attached collaborators
        such as the temporal client). Without this, such a change silently
        rewrites the behaviour of every later test, which shows up as unrelated
        401s, rewritten public URLs and assertions about a client that is
        supposed to be absent.
        """
        settings = self.app.state.settings
        for name, value in self._settings_snapshot.items():
            if getattr(settings, name, _MISSING) is not value:
                setattr(settings, name, value)
        backing = self._state_mapping()
        for name in [key for key in backing if key not in self._state_snapshot]:
            backing.pop(name, None)
        for name, value in self._state_snapshot.items():
            if backing.get(name, _MISSING) is not value:
                backing[name] = value

    def reset_storage(self) -> None:
        """Empty the shared object store between tests.

        The store used to be created per test, so tests could assert on the exact
        set of written objects. It now lives for the whole worker process and
        must be cleared, otherwise every later test sees the accumulated objects
        of its predecessors.
        """
        self.storage.objects.clear()
        self.storage.deleted_keys.clear()
        self.storage.ensured = False
        self.storage.fail_put = False

    def client(self) -> TestClient:
        """Enter the TestClient once and keep it open for the whole process.

        The lifespan disposes ``app.state.db_engine`` on shutdown, so the client
        must stay open across tests rather than being entered and exited per test.
        """
        if self._client is None:
            test_client = TestClient(self.app)
            test_client.__enter__()
            test_client.app_state["engine"] = self.engine
            test_client.app_state["sessionmaker"] = self.sessionmaker
            test_client.app_state["media_engine"] = self.media_engine
            test_client.app_state["media_sessionmaker"] = self.media_sessionmaker
            test_client.app_state["storage"] = self.storage
            self._client = test_client
        return self._client

    def close(self) -> None:
        if self._client is not None:
            self._client.__exit__(None, None, None)
            self._client = None
        asyncio.run(self.media_engine.dispose())
        asyncio.run(self.engine.dispose())


@pytest.fixture(scope="session")
def _session_application(
    postgres_worker_database_url: str, postgres_media_database_url: str
) -> Iterator[_SessionScopedApplication]:
    settings = Settings(
        database_url=postgres_worker_database_url,
        minio_endpoint="localhost:9000",
        minio_access_key="test",
        minio_secret_key="test",
        minio_bucket="test-bucket",
        web_login_workspace_id=AUTH_BOOTSTRAP_WORKSPACE_ID,
    )
    application = _SessionScopedApplication(settings, postgres_media_database_url)
    try:
        yield application
    finally:
        application.close()


@pytest.fixture
def client(
    _session_application: _SessionScopedApplication,
    postgres_seeded_database_url: str,
) -> TestClient:
    test_client = _session_application.client()
    # The client outlives a single test now, so cookies set by one test would
    # otherwise change the viewer's time zone for every later test in the worker.
    test_client.cookies.clear()
    _session_application.restore_settings()
    _session_application.reset_storage()
    return test_client


@pytest.fixture(autouse=True)
def reset_ingest_store() -> None:
    store_module.store = InMemoryIngestStore()


@pytest.fixture(autouse=True)
def reset_process_context_vars() -> Iterator[None]:
    """Clear request-scoped context shared by a reused application instance.

    The application, its engines and its storage live for the whole worker
    process now, so anything they keep outside the database would leak from one
    test to the next. These context variables carry the viewer's time zone and
    tracing ids; a test that sets a non-UTC zone would otherwise change the
    rendered time of every later test in the same worker.
    """
    for variable, default in _REQUEST_CONTEXT_DEFAULTS:
        variable.set(default)
    yield
    for variable, default in _REQUEST_CONTEXT_DEFAULTS:
        variable.set(default)
