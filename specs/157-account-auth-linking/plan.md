# Implementation Plan: Связанные способы входа

**Branch**: `157-account-auth-linking` | **Date**: 2026-08-16 | **Spec**:
[spec.md](spec.md)

## Summary

Расширить существующий passwordless email/OAuth auth flow безопасным linking и
отдельным recovery merge flow. Одинаковая почта не будет автоматически
сливать аккаунты. Пустой duplicate можно связать после двух proofs; при данных
в обоих аккаунтах пользователь подтверждает preview, а сервер сохраняет
контент и стабильные ID, оставляя workspace отдельными и блокируя конфликты
прав, billing, календаря и удаления.

## Technical Context

**Language/Version**: Python 3.13, Jinja HTML, Swift/macOS WebView

**Primary Dependencies**: FastAPI, SQLAlchemy async, Alembic, PostgreSQL,
existing OAuth adapters, existing Swift WebKit bridge

**Storage**: PostgreSQL/RLS, existing object storage references; no new content
storage

**Testing**: pytest/pytest-asyncio contract and integration suites, existing
macOS/WebView validation, `infra/scripts/ci-local.sh`

**Risk / Validation Lane**: `high-risk-feature` — auth, sessions, identity
linking, account data movement and high-risk UX.

**Release Gate**: no deployment in this slice; PR requires full local CI.
Production repair/deploy is a separate explicitly approved release task after
the merge recovery path is validated on disposable data.

**Target Platform**: production server plus browser cabinet and GRAF Local
embedded WebView

**Project Type**: multi-surface web service and macOS desktop client

**Performance Goals**: bounded preview and one transactional merge for a
single account pair; no content scan or similarity-based deduplication.

**Constraints**: preserve CSRF/state/nonce/rate limits/RLS, metadata-only
audit, no raw secrets, no partial mutation, no arbitrary session on ambiguity.

**Scale/Scope**: existing account and workspace tables; v1 handles one pair per
intent and does not introduce bulk migration or admin-side mass merge.

## Constitution Check

- Auth and privacy boundaries remain fail closed; proofs are stronger than
  email equality. **PASS**
- Existing tenant/workspace and RLS boundaries remain authoritative; workspaces
  are not merged. **PASS**
- No passwords, provider secrets, raw codes, meeting content or transcript text
  enter audit/spec/evidence. **PASS**
- User-visible blocked/error states remain localized, accessible and distinct
  from service unavailability. **PASS**
- Existing system-audio-first macOS product scope is unchanged. **PASS**
- Ponytail: reuse existing provider-link, callback, settings and audit helpers;
  add only merge intent/journal state required for a cross-account operation.
  **PASS**

## Validation Plan

1. Focused unit/contract tests for proof, state transitions, merge policy,
   idempotency, conflict blockers and safe rendering.
2. PostgreSQL integration tests for row locks, RLS, foreign-key reference
   preservation and zero mutation on blocked/cancelled/replayed intents.
3. Browser and embedded desktop route parity tests, including WebView navigation
   boundary and localized error states.
4. Run `quickstart.md` scenarios and `infra/scripts/ci-local.sh --fast`, then
   full `infra/scripts/ci-local.sh` before PR closeout.

## Project Structure

```text
specs/157-account-auth-linking/
├── spec.md
├── research.md
├── data-model.md
├── contracts/
│   ├── auth-linking.md
│   ├── merge.md
│   └── settings.md
├── quickstart.md
└── tasks.md

apps/server/src/twobrain_rec_server/
├── auth/
│   ├── provider_links.py
│   ├── callbacks.py
│   ├── sessions.py
│   └── account_merge.py           # new, only if existing helpers cannot hold it
├── cabinet/
│   ├── web_routes/auth.py
│   ├── web_routes/auth_email_flow.py
│   ├── web_routes/provider_links.py
│   ├── web_routes/settings.py
│   └── rendering.py
└── db/
    ├── models/federated_auth.py
    ├── models/identity.py
    └── migrations/versions/        # one additive migration

apps/server/tests/
├── unit/
├── contract/
└── integration/

apps/macos/RecApp/Sources/Cabinet/
└── EmbeddedCabinetWebView.swift    # only if parity fix is required
```

**Structure Decision**: server-owned account policy and transaction logic stay
in the existing auth/cabinet/db modules. The desktop client only preserves the
existing handoff and renders the same server-owned outcome; it does not gain a
second merge implementation.

## Delivery slices

### Slice A — safe conflict and existing link regression

Handle ambiguous email as a localized, non-500 recovery state; harden the
existing provider link flow and settings contract without changing data.

### Slice B — explicit merge preview/confirm

Add merge intent/journal, preflight and deterministic transaction with the
entity policy in the spec. Empty duplicate and data-preserving merge share the
same proof and audit machinery.

### Slice C — settings and desktop parity

Expose linked methods and unlink safeguards, then verify browser/WebView parity
and safe return/error behavior.

## Complexity Tracking

| Addition | Why needed | Simpler alternative rejected because |
| --- | --- | --- |
| `AccountMergeIntent` and journal | Cross-account proof, preview fingerprint, replay and audit need durable state. | Reusing OAuth callback state cannot bind two accounts or represent merge outcome safely. |
| Entity preflight blockers | Role, billing, calendar and deletion state cannot be safely inferred. | Copying all user FKs would cross tenant/security boundaries. |
