FROM python:3.13-slim-bookworm@sha256:9d7f287598e1a5a978c015ee176d8216435aaf335ed69ac3c38dd1bbb10e8d64 AS base

ARG GRAF_DEV_SOURCE_SHA
LABEL org.2brain.graf.dev.source-sha="${GRAF_DEV_SOURCE_SHA}"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    GRAF_DEV_SOURCE_SHA=${GRAF_DEV_SOURCE_SHA}

WORKDIR /app

RUN addgroup --system twobrain && adduser --system --ingroup twobrain twobrain

COPY apps/server/pyproject.toml apps/server/README.md apps/server/constraints.txt /app/
COPY apps/server/alembic.ini /app/alembic.ini
COPY apps/server/src /app/src
COPY apps/server/scripts /app/scripts

RUN pip install --constraint constraints.txt ".[evaluation]"

FROM base AS media-runtime

USER root

RUN sed -i \
      -e 's|http://deb.debian.org/debian-security|https://snapshot.debian.org/archive/debian-security/20260518T000000Z|g' \
      -e 's|http://deb.debian.org/debian|https://snapshot.debian.org/archive/debian/20260518T000000Z|g' \
      /etc/apt/sources.list.d/debian.sources \
    && printf 'Acquire::Check-Valid-Until "false";\n' > /etc/apt/apt.conf.d/99snapshot \
    && apt-get update \
    && apt-get install --no-install-recommends --yes ffmpeg=7:5.1.9-0+deb12u1 \
    && rm -rf /var/lib/apt/lists/* \
    && install -d -m 0700 -o twobrain -g twobrain /var/lib/twobrain-rec/playback-normalization

ENV TMPDIR=/var/lib/twobrain-rec/playback-normalization

USER twobrain

CMD ["python", "-m", "twobrain_rec_server.normalization.worker"]

FROM base AS runtime

USER twobrain

EXPOSE 8080

CMD ["uvicorn", "twobrain_rec_server.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8080", "--no-access-log"]
