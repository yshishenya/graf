# Implementation Plan: Provider Link Verified Callback

**Branch**: `100-provider-link-verified-callback` | **Date**: 2026-07-16 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/100-provider-link-verified-callback/spec.md`

## Summary

Replace direct client-supplied provider identity linking with a verified provider callback followed by an explicit GRAF confirmation. Reuse and extend the existing `WorkspaceProviderLinkState`: bind it to the initiating session and callback state, write candidate claims only from a verified provider adapter, and clear them after any terminal state. Keep ordinary login/signup on its existing resolver; dispatch link states to a dedicated resolver that cannot create an identity or change a login session before confirmation. Add the minimal browser Settings surface and reuse it inside the embedded desktop cabinet.

## Technical Context

**Language/Version**: Python >=3.13

**Primary Dependencies**: FastAPI, SQLAlchemy asyncio, Alembic, Pydantic, Jinja2

**Storage**: PostgreSQL with RLS; existing auth and cabinet tables

**Testing**: pytest unit/contract/integration, including real PostgreSQL RLS tests

**Risk / Validation Lane**: high-risk feature — it changes authentication, session binding, database RLS, audit and a user-facing settings flow.

**Release Gate**: `cd-remote.sh --dry-run` then `--execute` for the behavior release, because this changes production authentication behavior.

**Target Platform**: GRAF server, browser cabinet and existing embedded macOS cabinet

**Project Type**: server-rendered web application with REST API

**Performance Goals**: no additional provider round trip beyond existing callback verification; link state expires within the existing 15-minute callback window; confirmation performs one bounded database transaction.

**Constraints**: no raw identity proof from client input; exact user/workspace/session and callback-nonce RLS binding; CSRF for mutation; metadata-only audit; no auto-merge/ownership transfer; browser and embedded UI share server-owned templates.

**Scale/Scope**: existing enabled identity providers; one existing link-state table, auth callback path and Settings entry. Provider unlink, primary-provider management, account merging and a native Swift screen are out of scope.

## Constitution Check

**Before research — PASS.** No constitution amendment is needed. The feature does not alter capture, media egress, deletion or the parked audio-routing boundary. It must preserve the Constitution's authentication, secret, metadata-only diagnostics, high-risk Spec Kit and clean-room UI gates.

**After design — PASS.** The design keeps provider tokens/payloads server-side, uses the existing provider adapter, adds no dependency or desktop native auth path, and includes RLS, CSRF, audit-redaction, accessibility and release gates.

## Validation Plan

- TDD contract coverage for start, callback and confirm; legacy raw endpoint; normal login preservation; idempotence, conflict, expiry/replay and policy changes.
- PostgreSQL RLS integration proof for exact callback-nonce access, owner/user/workspace/session isolation, and zero-row update behavior.
- Audit-redaction assertions for every link lifecycle terminal state.
- Browser and embedded Settings contract/integration checks for CSRF, safe status copy, labelled controls, focus/status accessibility and parity.
- Expiry-scrub and narrow maintenance-command tests for abandoned pending claims; migration upgrade/downgrade and rollback tests proving the safe legacy `409` guard remains available.
- Feature quickstart, then `infra/scripts/ci-local.sh` before PR. On release, use the documented dry-run, production deploy and metadata-only smoke.

## Project Structure

### Documentation (this feature)

```text
specs/100-provider-link-verified-callback/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/provider-link-api.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/
├── src/twobrain_rec_server/auth/          # callback/session/policy services
├── src/twobrain_rec_server/api/auth.py    # REST start, callback, confirm
├── src/twobrain_rec_server/db/models/      # link state and identities
├── src/twobrain_rec_server/db/migrations/  # schema and RLS policy
├── src/twobrain_rec_server/cabinet/        # Settings queries, views, templates, routes
└── tests/{unit,contract,integration}/       # auth, RLS and browser/desktop parity
```

**Structure Decision**: Extend the existing server auth and cabinet modules. There is no separate frontend or macOS-native implementation because the embedded desktop cabinet already renders the server-owned settings surface.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | — | — |
