# Research: Server Ingest Foundation

## Decision: Python FastAPI server for ingest APIs

**Rationale**: The repository does not yet have a backend service, and FastAPI gives a compact path to typed HTTP contracts, OpenAPI generation, dependency injection, and file upload handling. Official FastAPI documentation supports file upload inputs through `UploadFile`, which fits server-mediated ingest where the backend receives data and validates it before writing to owner-controlled storage.

**Alternatives considered**: Go/Gin and Node/Fastify were viable for streaming APIs, but would add more repository/runtime variance before the core product contracts are stable. Reusing the macOS Swift package for server code was rejected because the service target is Docker/Linux.

## Decision: SQLAlchemy 2 async ORM plus Alembic for Postgres metadata

**Rationale**: Postgres is the product baseline for dedicated metadata storage. SQLAlchemy's asyncio extension supports async engines/sessions, which matches FastAPI's request model and lets upload/status endpoints avoid blocking on database I/O. Alembic provides versioned schema changes needed for Spec Kit tasks and future deletion/audit evolution.

**Alternatives considered**: Raw asyncpg would be lighter but would push schema mapping and transaction conventions into ad hoc code. Django ORM would add a larger web framework than this API slice needs.

## Decision: Server-mediated MinIO writes only

**Rationale**: 012 must not expose direct object-storage URLs or credentials to clients. The backend owns validation, tenant scoping, object keys, checksums, and finalization. MinIO remains the object storage backend, but the public contract is the 2brain Rec ingest API, not S3-compatible access from desktop clients.

**Alternatives considered**: Pre-signed/direct upload was deferred to `direct-object-upload` because it increases credential, expiry, and deletion-truth complexity. Local filesystem storage was rejected because the constitution and PRD require owner-controlled object storage suitable for self-hosted deployments.

## Decision: Application-level tenant isolation in 012, PostgreSQL RLS as explicit hardening gate

**Rationale**: The feature already needs provider-neutral org/workspace/user/device authorization checks at every ingest/status endpoint. Implementing those checks first keeps the MVP foundation smaller while preserving the security invariant. PostgreSQL Row Level Security is documented by PostgreSQL as a table-level policy mechanism for filtering/selecting/modifying rows; it should be implemented as `RLS-hardening` once the schema and tenant context propagation settle.

**Alternatives considered**: Enabling RLS immediately would be stronger defense in depth, but risks premature policy churn while auth provider and workspace models are not final. Omitting RLS entirely was rejected; it remains a named follow-up gate in PRD/status docs and must be handled or explicitly accepted before external customer use.

## Decision: No Temporal or MediaScribe runtime dependency in 012

**Rationale**: Clarification fixed the boundary: 012 records ingest readiness and processing placeholders only. The first workflow submission belongs to `015-mediascribe-processing-pipeline`. Therefore `GET /health/ready` for 012 checks API config, Postgres, MinIO, and ingest secrets/configuration, but not Temporal or MediaScribe availability.

**Alternatives considered**: Starting a lightweight Temporal workflow on finalize was rejected because it would silently pull processing scope into 012. Requiring Temporal in Docker Compose readiness was rejected for the same reason.

## Decision: Provider-neutral auth/device contracts

**Rationale**: 012 needs authenticated identity, workspace membership, and registered device context, but federated auth provider implementation is deferred to `013-federated-auth-foundation`. Contracts therefore describe required claims/context and server-side checks without selecting Yandex, VK, Telegram, Sber, T-ID, or any other provider.

**Alternatives considered**: Implementing a single temporary OAuth provider was rejected because it would blur the 013 boundary. Anonymous ingest was rejected because tenant and device checks are mandatory.

## Decision: Configurable ingest limits with internal MVP defaults

**Rationale**: The spec requires concrete configurable limits and truthful over-limit outcomes. Defaults are: 4 hour maximum recording duration, 2.5 GiB per track, 5 GiB total package, and 24 hour upload-session TTL. These values support 30-minute and 60-minute validation fixtures while leaving deployment-level room to tighten policy.

**Alternatives considered**: Unlimited ingest was rejected as unsafe for self-hosted resource control. Hard-coded limits were rejected because tenant/deployment policy must be adjustable.

## Decision: Metadata-only observability and audit

**Rationale**: The constitution requires Langfuse/diagnostics boundaries and no content leakage. In 012, logs and audit events may include IDs, status transitions, object keys, byte counts, duration, checksum identifiers, and error codes. They must not include raw audio, transcript text, bearer tokens, object-storage credentials, signed URLs, or secret values.

**Alternatives considered**: Rich debug payload logging was rejected because ingest touches sensitive audio and credential boundaries. No audit logging was rejected because deletion truth and operational support require traceable lifecycle metadata.

## References

- FastAPI file upload docs: https://fastapi.tiangolo.com/tutorial/request-files/
- SQLAlchemy asyncio docs: https://docs.sqlalchemy.org/20/orm/extensions/asyncio.html
- MinIO Python SDK API reference: https://min.io/docs/minio/linux/developers/python/API.html
- PostgreSQL Row Security Policies: https://www.postgresql.org/docs/17/ddl-rowsecurity.html
- Temporal Python SDK reference: https://python.temporal.io/
- Pydantic settings docs: https://docs.pydantic.dev/latest/api/pydantic_settings/
