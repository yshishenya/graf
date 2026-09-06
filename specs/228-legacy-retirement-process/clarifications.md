# Clarifications: Feature 228 legacy retirement process

**Date**: 2026-08-31
**Source**: Explicit product-owner directions recorded in this thread and the
existing GRAF governance baseline. No interactive question is pending.

## Resolved decisions

1. **No removal now.** Feature 228 designs and validates the process first;
   legacy runtime/data/history deletion is out of scope.
2. **Incremental retirement.** Old debt is retired in small, independently
   reviewable feature slices while new unowned legacy is blocked.
3. **One normal Dev application.** Retirement rehearsal happens in the shared,
   isolated Dev lifecycle; no parallel per-worktree installed application is
   introduced.
4. **Rare release trains.** A slice may receive fast CI while evolving; release
   evidence is exactly one authoritative Full CI after the release candidate is
   frozen.
5. **Bounded agent context.** Root `AGENTS.md` remains a stable router. Active
   feature/contour detail is read from the active Spec Kit path and scoped
   guidance, not written to root instructions.
6. **Reviewer ownership.** Checklists and issue closure remain reviewer/evidence
   actions. Agents may generate them but do not mark them complete.
7. **GitHub traceability.** A fresh Feature ID is allocated before a feature;
   every executable task has a canonical Russian GitHub issue and PR link.

## Deferred decisions that block a future removal slice, not Feature 228 planning

- Supported-client/data cutoff date and owner for each observed contour.
- Whether each candidate is a current product contract, a temporary compatibility
  exception, or actually removable.
- Domain-specific rollback targets and rehearsal environments for migrations,
  Temporal, MediaScribe history and Sparkle/update continuity.

These choices are deliberately recorded per contour after inventory. They must
not be guessed globally by an agent.
