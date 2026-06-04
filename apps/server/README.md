# 2brain Rec Server

Backend ingest foundation for finalized local recording artifacts.

The `012-server-ingest-foundation` slice is intentionally server-mediated: desktop clients call the 2brain Rec API, and the server writes validated bytes to owner-controlled MinIO. This service does not expose direct object-storage upload URLs, start Temporal workflows, call MediaScribe, or emit content-bearing diagnostics.

## Observability Boundary

Logs, problem responses, and audit metadata may include request IDs, tenant-scoped IDs, lifecycle statuses, byte counts, checksum identifiers, error codes, and timing information. They must not include raw audio, transcript text, bearer tokens, MinIO credentials, MediaScribe credentials, signed URLs, passwords, or live secret paths.

`012` readiness checks only API configuration, Postgres, MinIO, and ingest limits. Temporal and MediaScribe are intentionally not runtime readiness dependencies until later processing slices.

## Not Implemented In 012

The ingest foundation does not expose transcript download, summary download, audio download, public share links, login-required share pages, team-wide browsing, privileged admin review, dashboard meeting detail, deletion execution, indexing, or assisted auto-recording endpoints. Later slices may add those surfaces after the required access, processing, retention, and deletion specs are complete.
