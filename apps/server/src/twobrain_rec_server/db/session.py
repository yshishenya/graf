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


def create_system_admin_database(
    *, database_url: str,
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """Separate bounded pool; never fall back to the ordinary application URL."""
    from sqlalchemy.engine import make_url
    from sqlalchemy.exc import ArgumentError

    try:
        url = make_url(database_url)
    except (ArgumentError, ValueError):
        raise ValueError('system database URL is invalid') from None
    if url.drivername != 'postgresql+asyncpg' or url.username != 'twobrain_rec_system':
        raise ValueError('system database requires the twobrain_rec_system PostgreSQL login')
    engine = create_async_engine(
        url, pool_pre_ping=True, pool_size=4, max_overflow=0, pool_timeout=5,
        connect_args={'server_settings': {
            'row_security': 'on', 'statement_timeout': '2000',
            'idle_in_transaction_session_timeout': '10000',
        }},
    )
    return engine, async_sessionmaker(
        engine, expire_on_commit=False, info={'system_database': True},
    )


async def verify_system_admin_database_identity(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    async with sessionmaker() as session:
        safe = await session.scalar(text("""
            select session_user = 'twobrain_rec_system'
              and current_user = session_user and current_setting('row_security') = 'on'
              and not has_schema_privilege(session_user,'public','CREATE')
              and not (r.rolsuper or r.rolcreatedb or r.rolcreaterole or r.rolinherit
                       or r.rolreplication or r.rolbypassrls)
              and not exists (select 1 from pg_auth_members m
                              where m.member = r.oid or m.roleid = r.oid)
              and not exists (select 1 from pg_class c where c.relowner = r.oid)
              and not exists (select 1 from pg_namespace n where n.nspowner = r.oid)
            from pg_roles r where r.rolname = session_user
        """))
        from twobrain_rec_server.db.rls_validation import SYSTEM_CONTENT_COLUMNS

        gates = (await session.execute(text("""select c.relname from pg_policy p
            join pg_class c on c.oid=p.polrelid join pg_namespace n on n.oid=c.relnamespace
            where n.nspname='public' and c.relrowsecurity and c.relforcerowsecurity
              and not p.polpermissive and p.polcmd='r' and p.polname='system_content_gate'
              and (select oid from pg_roles where rolname=session_user)=any(p.polroles)"""))).scalars().all()
        safe = safe and set(gates) == set(SYSTEM_CONTENT_COLUMNS)
    if safe is not True:
        raise RuntimeError('system database identity verification failed')
