# Research: Desktop Upload Custody Architecture

## Decision: Keep 086 Read-Only Before Code

**Decision**: Stage one produces architecture evidence, contracts, and a
small-PR roadmap only.

**Rationale**: The flow touches upload retry, server ingest, deletion/local
purge, support evidence, and desktop/server trust boundaries. Moving code before
the map is complete risks changing custody truth.

**Alternatives considered**:

- Start with a direct split of `DesktopUploadQueueService.swift`: rejected
  because queue, support, local purge, and upload orchestration are currently
  coupled by product behavior.
- Start with more cabinet rendering cleanup: rejected because 085 shows lower
  product value after the recent cabinet PRs.

## Decision: Treat Upload Custody As The Next Product-Value Node

**Decision**: Prioritize desktop upload custody over smaller server-only
cleanup.

**Rationale**: The desktop upload flow is where local recording truth becomes
server custody. It also carries deletion local purge acknowledgement and
metadata-only support reporting. That is closer to product reliability than
cosmetic module shape.

**Alternatives considered**:

- Cabinet egress boundary first: valid lower-risk path, but lower product
  leverage than upload custody.
- Shared Swift model segmentation first: useful later, but does not directly
  reduce custody-flow risk.

## Decision: No `delete now` In Stage One

**Decision**: 086 may identify deletion candidates, but no delete is approved
without a later focused proof pass.

**Rationale**: Static search can miss Swift Codable contracts, persisted queue
state, route decorators, DTOs, and support/deletion lifecycle roles.

**Alternatives considered**:

- Delete low-reference helpers immediately: rejected because low reference count
  is not runtime evidence.

## Decision: Use Existing Test Surfaces As Future Gates

**Decision**: Future batches must reuse existing XCTest, server tests, contract
checks, and no-secret scans before adding new test infrastructure.

**Rationale**: Ponytail favors reuse. Existing tests already cover upload
client, custody projection, local purge, support incident fixtures, capture UI
copy, and server ingest/deletion/support behavior.

**Alternatives considered**:

- Add new architecture tooling: rejected unless existing `rg`, Swift tests,
  pytest, and repo scripts cannot prove a specific boundary.

## Decision: Split Roadmap By Behavior Boundary

**Decision**: Future batches should separate queue persistence/scheduling,
server transport, custody projection, local purge acknowledgement, and support
incident safety as separate PRs.

**Rationale**: These boundaries can be reviewed independently and have distinct
failure modes.

**Alternatives considered**:

- Split by file size alone: rejected because it can move coupled behavior into
  more files without reducing review risk.
