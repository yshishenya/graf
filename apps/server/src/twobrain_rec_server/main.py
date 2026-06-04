from fastapi import FastAPI

from twobrain_rec_server.api.ingest import router as ingest_router
from twobrain_rec_server.api.health import router as health_router
from twobrain_rec_server.api.problems import ProblemDetail, problem_exception_handler
from twobrain_rec_server.config import Settings, get_settings
from twobrain_rec_server.observability.logging import configure_logging, request_logging_middleware


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings)

    app = FastAPI(
        title="2brain Rec Server Ingest API",
        version="0.1.0",
        description="Backend ingest foundation for finalized local recording artifacts.",
    )
    app.state.settings = settings
    app.middleware("http")(request_logging_middleware)
    app.add_exception_handler(ProblemDetail, problem_exception_handler)
    app.include_router(health_router)
    app.include_router(ingest_router)
    return app


app = create_app()
