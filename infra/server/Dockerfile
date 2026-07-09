FROM python:3.13-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN addgroup --system twobrain && adduser --system --ingroup twobrain twobrain

COPY apps/server/pyproject.toml apps/server/README.md apps/server/constraints.txt /app/
COPY apps/server/alembic.ini /app/alembic.ini
COPY apps/server/src /app/src
COPY apps/server/scripts /app/scripts

RUN pip install --upgrade pip \
    && pip install --constraint constraints.txt "."

USER twobrain

EXPOSE 8080

CMD ["uvicorn", "twobrain_rec_server.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8080"]
