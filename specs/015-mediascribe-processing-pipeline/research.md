# Research: MediaScribe Processing Pipeline

## Decision: Use Temporal for durable processing orchestration

**Decision**: Start a Temporal workflow for each finalized meeting using a
non-sensitive workflow id derived from the internal meeting id, for example
`processing/<meeting_id>`.

**Rationale**: The constitution selects Temporal as the durable workflow engine.
Temporal documentation describes workflow ids as application-level business
process identifiers and warns not to include sensitive data or PII because ids
are visible in Web UI, CLI, event history, and logs. It also guarantees only one
open workflow execution per workflow id, and conflict/reuse policies provide
the duplicate-start behavior this feature needs.

**Alternatives considered**:

- FastAPI `BackgroundTasks`: rejected for the main processing path because it is
  request-lifecycle background work and is not sufficient for restart-safe,
  long-running, retryable MediaScribe processing.
- Plain database poller only: rejected as the primary product path because it
  would reimplement workflow durability and retry semantics already selected by
  the constitution.
- Client-started processing: rejected because desktop clients must not start
  workflows or know dependency credentials.

**Sources**:

- https://docs.temporal.io/workflow-execution/workflowid-runid
- https://docs.temporal.io/develop/python/client/temporal-client

## Decision: Keep non-deterministic I/O out of workflow code

**Decision**: Put MediaScribe HTTP calls, MinIO reads, Postgres writes, and
secret-file access in activities or service adapters. Keep workflow code limited
to deterministic orchestration and status transitions.

**Rationale**: Temporal Python docs state workflow code must remain
deterministic; non-deterministic work such as API calls and database queries
belongs in Activities that Temporal retries reliably.

**Alternatives considered**:

- Direct HTTP calls inside workflow code: rejected because replay can become
  non-deterministic.
- Database writes inside workflow orchestration: rejected for the same replay
  reason and for harder test isolation.

**Source**: https://docs.temporal.io/develop/python/workflows/versioning

## Decision: Use HTTPX with explicit timeouts and application-level retry mapping

**Decision**: Implement MediaScribe HTTP access with HTTPX, explicit connect/
read/write/pool timeouts, and application-level retry/error mapping for 409,
413, 429, 5xx, malformed responses, and network failures.

**Rationale**: HTTPX enforces timeouts by default and allows custom timeout
configuration. Its built-in transport retries cover connect errors and connect
timeouts only, so status-code and read/write retry semantics must live in the
processing client/workflow policy.

**Alternatives considered**:

- Rely only on HTTPX transport retries: rejected because it does not cover
  MediaScribe status-code retry policy.
- Disable timeouts: rejected because processing must fail safely and recover
  rather than hang indefinitely.

**Sources**:

- https://www.python-httpx.org/advanced/timeouts/
- https://www.python-httpx.org/advanced/transports/

## Decision: Preserve `012` ingest success independently from processing

**Decision**: MediaScribe and Temporal availability affects only processing
state. A valid finalized ingest remains `ingested_pending_processing` or later
content-ready state even when processing is blocked, retrying, or failed.

**Rationale**: `012` explicitly accepted ingest as durable owner-controlled
storage with inert processing placeholders. Changing ingest truth because an
external dependency is unavailable would make uploaded/local file safety
misleading.

**Alternatives considered**:

- Fail finalized ingest if MediaScribe is unavailable: rejected because `012`
  already separated ingest readiness from processing readiness.
- Hide processing failures from meeting state: rejected because future dashboard
  and deletion truth require explicit dependency status.

## Decision: Do not request or expose 2brain notes in `015`

**Decision**: Request/import transcript and diarization as the MVP processing
outputs. Record summary dependency state as `not_requested`, `available`,
`unavailable`, or `failed`; do not expose generated notes or user-facing summary
surfaces in this slice.

**Rationale**: The local MediaScribe contract recommends `summarize=false` when
2brain Rec owns summaries. Current product status reserves dashboard/notes for
`016`. This lets `015` remain the transcription pipeline and still preserve
truth if MediaScribe returns summary metadata.

**Alternatives considered**:

- Request MediaScribe summary and expose it as notes: rejected as dashboard/notes
  scope drift.
- Drop summary fields completely: rejected because deletion and future result
  accounting should know whether the external dependency produced summary data.

## Decision: Store transcript content only in controlled server result stores

**Decision**: Imported transcript and diarization text may be stored in dedicated
server result tables or controlled objects, but default logs, diagnostics,
status responses, audit metadata, and external observability must remain
metadata-only.

**Rationale**: The constitution requires owner-controlled data boundaries and
metadata-only Langfuse traces by default. Processing status is useful to future
UI, but content belongs in explicit content stores with later access/download
policies.

**Alternatives considered**:

- Put transcript snippets in status responses: rejected because `016/017` access
  control is not yet accepted.
- Log imported text for debugging: rejected because it violates secret/content
  evidence policy.
