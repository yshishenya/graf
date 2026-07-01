# Research: Dead Code Batch 5

## Decision: Keep the batch import-only

Rationale: The next safest cleanup after prior helper/import batches is another
small import deletion pass with compile evidence. It reduces source surface
without changing behavior in capture-adjacent shared code.

Alternatives considered:
- Delete private helpers from shared routing code: rejected for this batch
  because caller/runtime evidence was not stronger than compile-proven import
  deletion.
- Split larger Swift files: deferred; splitting can change review boundaries
  and should remain a separate Spec Kit slice.
- Add or enable an unused-import linter: rejected; a new tool is larger than
  the cleanup.

## Decision: Use compile evidence as the deletion threshold

Rationale: Text scans are useful triage, but Swift imports can provide
property wrappers, protocol conformances, string helpers, and platform symbols
that are not obvious from token matching. A source line is deleted only after a
successful build and focused validation.

Alternatives considered:
- Remove every statically suspicious `Foundation` import: rejected because it
  optimizes line count over product safety.
- Replace broad imports with narrower imports: deferred unless it also removes
  source lines or fixes a concrete issue.

## Decision: No data model, contracts, release, or deploy

Rationale: The slice does not change schemas, runtime contracts, external
interfaces, product UX, or production infrastructure.

Alternatives considered:
- Create placeholder contracts/data-model files: rejected as documentation
  noise.
- Release immediately after cleanup: rejected; this cleanup can merge without a
  production deploy.
