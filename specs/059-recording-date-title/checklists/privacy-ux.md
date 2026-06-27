# Privacy And UX Checklist: Recording Date And Smart Title

**Purpose**: Validate that app/date naming requirements are safe enough before implementation planning continues.
**Created**: 2026-06-26
**Feature**: [spec.md](../spec.md)

## Metadata Collection

- [x] Calendar title use is deferred to feature 060.
- [x] Window/browser title use is deferred to a later privacy-sensitive slice.
- [x] Raw rejected window titles are not collected or required in committed evidence.
- [x] No new app/window observer or permission prompt is required only to name a recording.
- [x] Transcript-derived or LLM-inferred titles are out of scope.

## Privacy Copy And Control

- [x] Descriptive titles can be suppressed by policy.
- [x] Generic app/date fallback exists when descriptive naming is unsafe.
- [x] Explicit user-confirmed title replacement takes precedence without changing recording identity.
- [x] Evidence remains metadata-only and excludes raw audio, transcript text, URLs, emails, tokens, and private meeting content.

## User Experience

- [x] New recordings show the recording date, not upload or processing date.
- [x] Legacy meetings without title/date have truthful fallback states.
- [x] Safe filename basename is separated from storage identity.
- [x] Meeting list/search/sort expectations are covered by the spec and quickstart.

## Implementation Recheck - 2026-06-27

- [x] Resolver inputs are limited to persisted recording instants, local
  recording/session identity, already-approved app/platform context, and an
  optional explicit user-confirmed title contract.
- [x] Feature 059 does not introduce calendar API calls, calendar event
  matching, window-title collection, browser-tab title collection, or a new
  foreground app observer.
- [x] Unsafe title-like values are suppressed locally and rejected at server
  ingest without committing the rejected raw value to evidence.
- [x] Request validation errors use metadata-only problem responses, so invalid
  control-character title input is not echoed back from the API boundary.
- [x] Diagnostic evidence records only title provenance/status/source/confidence,
  suppressed-source metadata, lengths, dates, and stable suffixes; it excludes
  raw generated titles and safe basenames.
- [x] User-confirmed title compatibility preserves local recording id, media
  revision id, upload idempotency key, required package files, and server object
  identity.
