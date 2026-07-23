from collections.abc import AsyncIterator, Callable
from urllib.parse import unquote, urlsplit

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from twobrain_rec_server.config import Settings, get_settings
from twobrain_rec_server.db.tenant_context import (
    MaintenanceTenantContext,
    maintenance_context_settings,
)


def create_engine(
    settings: Settings | None = None,
    *,
    database_url: str | None = None,
) -> AsyncEngine:
    settings = settings or get_settings()
    return create_async_engine(database_url or settings.database_url, pool_pre_ping=True)


def create_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


def create_prompt_optimization_database(
    settings: Settings | None = None,
    *,
    actor_id: str = "graf-prompt-optimization-worker",
    reason_category: str = "prompt_optimization",
) -> tuple[AsyncEngine, Callable[..., AsyncSession]]:
    """Create an RLS-scoped database pair for deployment-global optimization."""

    settings = settings or get_settings()
    database_url = settings.prompt_optimization_database_url
    if not database_url:
        raise RuntimeError(
            "prompt optimization requires prompt_optimization_database_url"
        )
    try:
        database_user = unquote(urlsplit(database_url).username or "")
    except ValueError as exc:
        raise RuntimeError("prompt optimization maintenance database URL is invalid") from exc
    if database_user != "twobrain_rec_maintenance":
        raise RuntimeError(
            "prompt optimization requires the twobrain_rec_maintenance database role"
        )
    context = MaintenanceTenantContext(
        operation_name="prompt_optimization",
        actor_id=actor_id,
        reason_category=reason_category,
        feature_area="prompt_optimization",
    )
    engine = create_engine(settings, database_url=database_url)
    base_sessionmaker = create_sessionmaker(engine)
    context_settings = maintenance_context_settings(context)

    def sessionmaker(*args, **kwargs):
        session = base_sessionmaker(*args, **kwargs)
        sync_session = getattr(session, "sync_session", session)
        info = getattr(sync_session, "info", None)
        if isinstance(info, dict):
            info["tenant_context"] = dict(context_settings)
        return session

    return engine, sessionmaker


async def verify_prompt_optimization_database_identity(
    sessionmaker: Callable[..., AsyncSession],
) -> None:
    """Fail closed if the operations container is not using the guarded role."""

    async with sessionmaker() as session:
        row = (
            await session.execute(
                text("select current_user, current_setting('row_security', true)")
            )
        ).one()
    if row[0] != "twobrain_rec_maintenance" or row[1] != "on":
        raise RuntimeError("prompt optimization database identity verification failed")


async def get_db_session() -> AsyncIterator[AsyncSession]:
    sessionmaker = get_settings_sessionmaker()
    async with sessionmaker() as session:
        yield session


_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_settings_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _engine, _sessionmaker
    if _sessionmaker is None:
        _engine = create_engine()
        _sessionmaker = create_sessionmaker(_engine)
    return _sessionmaker
