# API And Contract Checklist: MediaScribe Processing Pipeline

**Purpose**: Validate requirement quality for processing status APIs, internal pickup contracts, MediaScribe mapping, lifecycle events, and future client boundaries.
**Created**: 2026-06-11
**Feature**: [spec.md](../spec.md)

**Note**: This checklist tests the requirements themselves, not the implementation.

## Requirement Completeness

- [x] CHK001 Are content-safe processing status fields defined for future clients without transcript text or dependency credentials? [Completeness, OpenAPI Contract]
- [x] CHK002 Are internal pickup request/response semantics defined without making desktop clients workflow owners? [Completeness, OpenAPI Contract]
- [x] CHK003 Are problem responses represented for auth denial, conflicts, dependency outages, and validation failures? [Completeness, OpenAPI Contract]
- [x] CHK004 Are MediaScribe submit fields mapped from canonical 2brain Rec track roles? [Completeness, MediaScribe Contract]
- [x] CHK005 Are lifecycle event names and required metadata defined for audit/status traceability? [Completeness, Lifecycle Events Contract]

## Requirement Clarity

- [x] CHK006 Is it clear that processing status may reveal availability and safe reasons but not transcript content? [Clarity, Spec FR-017/FR-018]
- [x] CHK007 Are exact MediaScribe job ids treated as server dependency references rather than user-facing identifiers? [Clarity, Lifecycle Events Contract]
- [x] CHK008 Are response fields stable enough for `016` dashboard work without implementing `016` surfaces now? [Traceability, OpenAPI Contract]
- [x] CHK009 Are endpoint authorization boundaries explicit enough for tenant-safe implementation tasks? [Security, Spec FR-026/OpenAPI]

## Scenario Coverage

- [x] CHK010 Are not-submitted, started, submitted, polling, importing, processed, blocked, failed, and canceled states represented in API vocabulary? [Coverage, OpenAPI ProcessingState]
- [x] CHK011 Are unknown/malformed MediaScribe statuses mapped to safe retryable or terminal processing states? [Coverage, MediaScribe Contract]
- [x] CHK012 Are no-dashboard/no-download/no-share/no-delete boundaries reflected in quickstart validation? [Scope, Quickstart]

## Acceptance Criteria Quality

- [x] CHK013 Are contract tests called out for API drift and MediaScribe request/response mapping? [Measurability, Quickstart]
- [x] CHK014 Are status responses measurable for 0 content/secret leaks? [Measurability, Spec SC-007/OpenAPI]
- [x] CHK015 Are future consumers given enough status truth without requiring implementation-specific database shape? [Clarity, OpenAPI/Data Model]
