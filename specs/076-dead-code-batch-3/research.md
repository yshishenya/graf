# Research: Dead Code Batch 3

## Decision: Skip New Static-Analysis Dependencies

**Rationale**: `swiftc` in this environment does not support
`-warn-unused-imports`, and adding SwiftLint or another analyzer would increase
tooling for a tiny deletion batch. Ponytail favors compiler probes over new
dependencies here.

**Alternatives considered**:

- Add a new linter: rejected because it broadens the batch and dependency
  surface.
- Hand-edit broad imports: rejected unless `swift build` proves the deletion.

## Decision: Use Import-Only Compile Probes

**Rationale**: After 074 and 075, simple one-reference private helper scans are
empty. Import-only probes are the next smallest safe cleanup because the Swift
compiler directly proves whether each import is still required.

**Alternatives considered**:

- Delete one-match test classes or tool entry-point types: rejected because
  XCTest discovery and `@main`/tool contracts are runtime/compiler entry points.
- Split large SwiftUI files: rejected for this batch because it changes
  structure without reducing code.

## Decision: Keep `ExperimentalPassthroughCoordinator` Import

**Rationale**: Removing its `Foundation` import caused compile errors for
`ObservableObject` and `@Published`. The import is therefore classified as
`keep intentionally` for this batch.

**Alternatives considered**:

- Replace with `import Combine`: deferred because it is a neutral import swap,
  not a deletion, and this batch is deletion-only.
