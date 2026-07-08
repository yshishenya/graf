# Requirements Checklist: 092 Automatic Meeting Detection

**Date**: 2026-07-08

## Completeness

- [x] User stories cover native app detection, browser detection, Russian-market
  registry coverage, false-positive suppression, metadata-only evidence,
  target-scoped auto-record, telemetry, and admin review.
- [x] Functional requirements define detector modes, registry modes, prompt
  behavior, auto-record opt-in, telemetry upload, admin review, and fail-closed
  behavior.
- [x] Success criteria include prompt timing, false-positive safety, forbidden
  content scans, resource gates, candidate upload filtering, and admin review.
- [x] Out-of-scope items exclude hidden capture, broad auto-record, bot join,
  participant notice prompts, MediaScribe submission changes, and Windows runtime
  support.
- [x] Clarification decisions resolve Tier A target choices, browser strategy,
  target identity granularity, debounce contract, and implementation slice order.

## Clarity

- [x] "Prompt-enabled", "diagnostic-only", "manual/browser-only", and
  "blocked-missing-bundle" have product behavior attached.
- [x] Unknown apps are explicitly discovery-only and cannot prompt or record.
- [x] Browser mic attribution is explicitly insufficient for browser meeting
  detection.
- [x] Target-scoped auto-record identity is defined for native and browser
  targets.
- [x] Telemetry upload is automatic only after VKS-candidate filtering and can be
  disabled by workspace/admin policy without breaking manual recording.

## Traceability

- [x] `registry-telemetry.md` traces FR-049 through FR-060 to concrete server,
  admin, and client behavior.
- [x] `fingerprints.md` and `native-allowlist.md` trace known app evidence and
  promotion rules.
- [x] JSON schemas define the registry, telemetry, and admin review payloads.
- [x] `data-model.md` maps contracts to server tables and macOS local documents.
- [x] `quickstart.md` maps success criteria to focused validation scenarios.

## Consistency

- [x] Automatic telemetry upload does not conflict with privacy boundaries because
  client-side VKS filtering occurs before raw unknown app identity leaves the
  device.
- [x] Remote registry cannot disable compiled safety gates.
- [x] Admin review can create `diagnostic_only` drafts but cannot auto-promote
  unknown candidates to `prompt_enabled`.
- [x] Server/admin first implementation order matches the need for a review queue
  before client uploader rollout.
- [x] Windows fingerprints remain future development data, not first-release
  runtime support.
