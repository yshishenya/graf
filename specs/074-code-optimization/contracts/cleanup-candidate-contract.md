# Cleanup Candidate Contract

A cleanup candidate can be changed only when this contract is satisfied.

## Required Evidence

- Candidate path and symbol/block name are recorded.
- Caller search covers the owning package and likely external entrypoints.
- Import/reference search covers tests, scripts, templates, Docker/infra, and
  macOS/package targets when relevant.
- Runtime route or command registration is checked when the candidate is exposed
  indirectly.
- The risk surface is named.

## Classification

- `delete now`: no active caller/runtime entrypoint and focused validation exists.
- `shrink now`: duplicate or redundant code can be expressed with existing code
  and focused validation exists.
- `keep intentionally`: looks unused but is a contract, test fixture, public
  entrypoint, external hook, migration, or safety guard.
- `risky / needs spec`: evidence is incomplete or the change touches behavior,
  data lifecycle, capture, auth, privacy, deletion, AI, storage, desktop, or
  deploy semantics.

## Acceptance

- Net runtime LOC delta for the batch is zero or lower.
- No new dependency is added.
- Existing tests are not weakened.
- Focused validation and required repository gate pass.
- PR lists removed, kept, and deferred candidates.
