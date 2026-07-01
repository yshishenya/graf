# Research: Dead Code Batch 4

## Decision: Continue with import-only deletion

Rationale: After 074 and 075, direct zero-reference helper scans no longer
produce a safer larger deletion target. Swift unused imports are still real
source surface, and SwiftPM build can prove whether a candidate import is
required.

Alternatives considered:
- Split large SwiftUI files: deferred, because it can change review and UI
  behavior boundaries.
- Add an unused-import linter: rejected for this batch; a new tool is larger
  than the source cleanup.
- Broad automated import rewrite: rejected; each candidate must keep compile
  evidence and focused validation.

## Decision: Keep compile-contract imports intentionally

Rationale: Static text scans are not enough for Swift. Some imports provide
compiler-visible protocols, property wrappers, platform types, or Foundation
aliases that are easy to miss.

Alternatives considered:
- Remove every statically suspicious import: rejected because that optimizes
  for line count over safety.
- Replace `Foundation` with narrower imports in this slice: deferred unless a
  direct replacement is smaller and proven necessary.

## Decision: No deploy for 077

Rationale: The batch changes source cleanliness only. It does not alter server
runtime, infra, configuration, or product release state.

Alternatives considered:
- Release immediately after cleanup: rejected; cleanup can merge without a
  production deploy.
