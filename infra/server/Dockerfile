FROM python:3.13-slim-bookworm@sha256:9d7f287598e1a5a978c015ee176d8216435aaf335ed69ac3c38dd1bbb10e8d64 AS dependencies

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
RUN addgroup --system twobrain && adduser --system --ingroup twobrain twobrain
COPY apps/server/constraints.txt /app/constraints.txt
RUN pip install --requirement constraints.txt

FROM dependencies AS application
COPY apps/server/pyproject.toml apps/server/README.md /app/
COPY apps/server/alembic.ini /app/alembic.ini
COPY apps/server/src /app/src
COPY apps/server/scripts /app/scripts
RUN pip install --no-deps --prefix=/install ".[evaluation]"
COPY infra/scripts/dev-migration-preflight.py /app/scripts/dev-migration-preflight.py

FROM dependencies AS media-dependencies
RUN sed -i \
      -e 's|http://deb.debian.org/debian-security|https://snapshot.debian.org/archive/debian-security/20260518T000000Z|g' \
      -e 's|http://deb.debian.org/debian|https://snapshot.debian.org/archive/debian/20260518T000000Z|g' \
      /etc/apt/sources.list.d/debian.sources \
    && printf 'Acquire::Check-Valid-Until "false";\n' > /etc/apt/apt.conf.d/99snapshot \
    && apt-get update \
    && apt-get install --no-install-recommends --yes ffmpeg=7:5.1.9-0+deb12u1 \
    && rm -rf /var/lib/apt/lists/* \
    && install -d -m 0700 -o twobrain -g twobrain /var/lib/twobrain-rec/playback-normalization

FROM media-dependencies AS media-runtime
COPY --from=application /install/ /usr/local/
COPY --from=application /app/ /app/
ARG GRAF_DEV_SOURCE_SHA
LABEL org.2brain.graf.dev.source-sha="${GRAF_DEV_SOURCE_SHA}"
ENV GRAF_DEV_SOURCE_SHA=${GRAF_DEV_SOURCE_SHA} \
    TMPDIR=/var/lib/twobrain-rec/playback-normalization
USER twobrain
CMD ["python", "-m", "twobrain_rec_server.normalization.worker"]

FROM dependencies AS runtime
COPY --from=application /install/ /usr/local/
COPY --from=application /app/ /app/
ARG GRAF_DEV_SOURCE_SHA
LABEL org.2brain.graf.dev.source-sha="${GRAF_DEV_SOURCE_SHA}"
ENV GRAF_DEV_SOURCE_SHA=${GRAF_DEV_SOURCE_SHA}
USER twobrain
EXPOSE 8080
# The only trusted proxy is the host nginx bound to loopback: it overwrites
# X-Forwarded-For with $remote_addr before forwarding to 127.0.0.1:18081.
# Never widen this to '*' or a container network: that would let an external
# caller spoof the operator/internal classification through forwarded headers.
CMD ["uvicorn", "twobrain_rec_server.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8080", "--no-access-log", "--proxy-headers", "--forwarded-allow-ips", "127.0.0.1"]
