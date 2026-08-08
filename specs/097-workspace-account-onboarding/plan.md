# Implementation Plan: Workspace Account Onboarding

**Branch**: `097-workspace-account-onboarding` | **Date**: 2026-07-17 | **Spec**: [spec.md](spec.md)

## Summary

Make ordinary sign-up create a private personal workspace instead of adding a
new person to the configured bootstrap workspace. Keep a corporate join as a
separate, explicit invitation acceptance. Reuse the existing workspace,
membership, invitation, session, RLS and audit primitives; add only the
personal-workspace marker, a narrow invitation-offer lifecycle, and a server-
verified active-workspace switch. Existing recordings and memberships are not
moved by this feature.

## Technical Context

**Language/Version**: Python 3.12; Swift 6 for the existing macOS client

**Primary Dependencies**: FastAPI, SQLAlchemy async, Alembic, Jinja cabinet,
PostgreSQL RLS, pytest, XCTest

**Storage**: PostgreSQL; existing `organizations`, `workspaces`,
`user_identities`, `workspace_memberships`, invitation and session tables

**Testing**: pytest unit/contract/integration and PostgreSQL migration/RLS
receipts; focused browser cabinet tests; existing Swift tests where a desktop
session contract changes

**Risk / Validation Lane**: high-risk feature — changes account creation,
authorization, sessions, RLS-protected data, onboarding and admin invitation
semantics. A metadata-only legacy report is a release precondition before the
new personal-space behavior is enabled for existing accounts.

**Release Gate**: `infra/scripts/ci-local.sh`, then approved
`infra/scripts/cd-remote.sh --dry-run` and production deploy/smoke. A migration
backup, rollback plan and metadata-only evidence are required.

**Target Platform**: GRAF server and browser cabinet; macOS consumes the same
server-issued workspace scope and must fail safely when it becomes invalid.

**Project Type**: Dockerized FastAPI web service with a native macOS client

**Performance Goals**: sign-up, offer retrieval, acceptance and workspace
switch need one bounded transaction each; no workspace-wide scans in a
request; no extra provider call after verified callback.

**Constraints**: no user-facing raw workspace ID; no automatic corporate join;
no account or recording reassignment; no auth tokens, codes, email lists or
private workspace data in evidence; server is authoritative for scope.

**Scale/Scope**: one self-hosted GRAF organization per deployment in v1. A
user can have one personal workspace and zero or more corporate memberships in
that organization. Cross-organization identity federation is not introduced.

## Constitution Check

**Before design: PASS.** This feature does not alter capture or egress. It
changes privacy and authorization boundaries, so it preserves server-side
membership validation, metadata-only audit, visible onboarding states and the
full high-risk release gate.

**After design: PASS.** The design reuses RLS-scoped tables and server-issued
sessions. It rejects automatic corporate enrollment, does not move records,
and makes revoked access fail closed. No new dependency, client-side authority
or direct desktop egress is introduced.

## Validation Plan

1. Migration tests upgrade and downgrade the personal-space and join-offer
   schema, including PostgreSQL RLS isolation.
2. Contract and integration tests cover new B2C email/provider registration,
   repeat verification, multiple invitations, explicit accept/reject, revoked
   access, last-owner protection and active-workspace switching.
3. Browser cabinet tests prove no raw workspace ID is required or rendered,
   personal space is visible, offers are explicit and inaccessible spaces do
   not leak data.
4. Exercise the desktop scoped-session recovery contract with a revoked
   corporate membership.
5. Run the feature quickstart and `infra/scripts/ci-local.sh` before PR;
   collect only metadata-only deploy/browser evidence after an approved deploy.

## Project Structure

```text
apps/server/
├── src/twobrain_rec_server/
│   ├── auth/                 # session, provider callback and policy flow
│   ├── admin/invitations.py  # invitation lifecycle, no auto-completion
│   ├── cabinet/              # browser onboarding and workspace switch UI
│   └── db/
│       ├── models/           # workspace/account/join-offer records
│       └── migrations/versions/
└── tests/
    ├── contract/
    ├── integration/
    └── unit/

apps/macos/
└── Shared/                   # only if the scoped-session recovery contract changes

specs/097-workspace-account-onboarding/
├── research.md
├── data-model.md
├── contracts/workspace-onboarding-api.md
├── quickstart.md
└── tasks.md
```

**Structure Decision**: keep authorization and account lifecycle in the
existing server modules. Do not introduce a second identity service or a
client-side active-workspace store.

## Complexity Tracking

No constitution exception. The only schema addition is needed to distinguish a
private workspace from a corporate one and to store an explicit invitation
offer; reusing implicit membership or a browser cookie would reintroduce the
unsafe automatic join path.
