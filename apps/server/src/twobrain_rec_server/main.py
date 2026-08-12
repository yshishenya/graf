from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles

from twobrain_rec_server.admin.templates import ADMIN_STATIC_URL, admin_static_dir
from twobrain_rec_server.admin.web import router as admin_web_router
from twobrain_rec_server.api.admin import router as admin_api_router
from twobrain_rec_server.api.auth import router as auth_router
from twobrain_rec_server.api.billing import router as billing_router
from twobrain_rec_server.api.cabinet import router as cabinet_api_router
from twobrain_rec_server.api.calendar import router as calendar_router
from twobrain_rec_server.api.health import router as health_router
from twobrain_rec_server.api.ingest import router as ingest_router
from twobrain_rec_server.api.meeting_detection import router as meeting_detection_router
from twobrain_rec_server.api.problems import (
    ProblemDetail,
    problem_exception_handler,
    request_validation_exception_handler,
)
from twobrain_rec_server.api.processing import router as processing_router
from twobrain_rec_server.api.product_analytics import router as product_analytics_router
from twobrain_rec_server.api.product_analytics_guard import ProductAnalyticsIngressGuard
from twobrain_rec_server.api.support_incidents import router as support_incidents_router
from twobrain_rec_server.cabinet.templates import CABINET_STATIC_URL, cabinet_static_dir
from twobrain_rec_server.cabinet.web import router as cabinet_web_router
from twobrain_rec_server.config import Settings, get_settings
from twobrain_rec_server.db.session import create_engine, create_sessionmaker
from twobrain_rec_server.observability.logging import configure_logging, request_logging_middleware
from twobrain_rec_server.public.templates import (
    PUBLIC_STATIC_URL,
    VersionedPublicStaticFiles,
    public_static_dir,
)
from twobrain_rec_server.public.web import router as public_web_router
from twobrain_rec_server.storage.minio_client import get_storage
from twobrain_rec_server.support.incidents import support_incident_configuration_status


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings)
    engine = create_engine(settings)
    storage = get_storage(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            yield
        finally:
            close_storage = getattr(app.state.storage, "close", None)
            if close_storage is not None:
                close_storage()
            await app.state.db_engine.dispose()

    production = settings.env.lower() == "production"
    app = FastAPI(
        title="GRAF Server Ingest API",
        version="0.1.0",
        description="Backend ingest foundation for finalized local recording artifacts.",
        docs_url=None if production else "/docs",
        redoc_url=None if production else "/redoc",
        openapi_url=None if production else "/openapi.json",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.db_engine = engine
    app.state.db_sessionmaker = create_sessionmaker(engine)
    app.state.storage = storage
    app.state.web_csrf_secret = settings.web_csrf_secret
    app.state.support_incident_integration_status = support_incident_configuration_status(settings)
    app.middleware("http")(request_logging_middleware)
    app.add_middleware(ProductAnalyticsIngressGuard)
    app.add_exception_handler(ProblemDetail, problem_exception_handler)
    app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
    app.mount(ADMIN_STATIC_URL, StaticFiles(directory=admin_static_dir()), name="admin_static")
    app.mount(CABINET_STATIC_URL, StaticFiles(directory=cabinet_static_dir()), name="cabinet_static")
    app.mount(
        PUBLIC_STATIC_URL,
        VersionedPublicStaticFiles(directory=public_static_dir()),
        name="public_static",
    )
    app.include_router(public_web_router)
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(billing_router)
    app.include_router(ingest_router)
    app.include_router(meeting_detection_router)
    app.include_router(processing_router)
    app.include_router(product_analytics_router)
    app.include_router(calendar_router)
    app.include_router(support_incidents_router)
    app.include_router(admin_api_router)
    app.include_router(cabinet_api_router)
    app.include_router(admin_web_router)
    app.include_router(cabinet_web_router)
    return app
