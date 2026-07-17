import logging
from types import SimpleNamespace

from fastapi import FastAPI

from twobrain_rec_server.observability.logging import JsonFormatter, request_logging_middleware

request_handler = logging.StreamHandler()
request_handler.setFormatter(JsonFormatter())
request_logger = logging.getLogger("twobrain_rec.request")
request_logger.handlers = [request_handler]
request_logger.setLevel(logging.INFO)
request_logger.propagate = False

app = FastAPI()
app.state.settings = SimpleNamespace(
    redact_headers=("authorization", "cookie", "set-cookie", "x-content-sha256")
)
app.middleware("http")(request_logging_middleware)


@app.get("/health/{item_id}")
async def health(item_id: str) -> dict[str, bool]:
    return {"ok": True}
