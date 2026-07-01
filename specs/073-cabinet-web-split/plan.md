# Implementation Plan: Cabinet Web Split

**Branch**: `codex/073-cabinet-web-split` | **Date**: 2026-07-01 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/073-cabinet-web-split/spec.md`

**Lane**: Significant architecture / high-risk behavior-preserving refactor.

## Summary

073 implements the first 072 roadmap batch, RB-072-01: split the oversized
server-rendered cabinet web router into smaller route-family modules while
preserving product behavior. The public import
`twobrain_rec_server.cabinet.web.router` remains stable for `main.py`.

Ponytail shape: reuse the existing FastAPI router/dependencies/renderers/tests,
add no new dependency, and avoid broader cleanups. The only intended runtime
change is code organization inside the cabinet web route layer.

## Technical Context

**Language/Version**: Python 3.13 server code.

**Primary Dependencies**: Existing FastAPI, SQLAlchemy asyncio, Jinja/rendering
helpers, Pydantic/schema types, existing auth/deletion/calendar/cabinet modules.
No new dependencies.

**Storage**: No storage change. Existing Postgres/MinIO/session behavior is
preserved through existing dependencies.

**Testing**: Focused pytest gates for cabinet route contracts, CSRF, HX
fragments, meeting list/detail, owner session, deletion/reporting, no-secret
content egress, plus `git diff --check`.

**Risk / Validation Lane**: Significant architecture / high-risk
behavior-preserving refactor. Although the diff should be mostly move/split
work, the route layer touches auth/session, CSRF, deletion/retention truth,
calendar settings, desktop WebView routes, and user-facing cabinet pages.

**Release Gate**: No production deploy for 073 unless separately requested.

**Target Platform**: Server web/API runtime in the self-hosted backend.

**Project Type**: Python FastAPI backend with server-rendered cabinet pages.

**Performance Goals**: No runtime performance change. Route dispatch and
rendering behavior should stay equivalent.

**Constraints**: Preserve every existing cabinet web route path, method,
response class, redirect/status behavior, dependency guard, HX fragment behavior,
and desktop route. Do not change templates, view-model semantics, egress,
deletion service, auth provider behavior, migrations, dependencies, infra, or
release files.

**Scale/Scope**: Primary file is
`apps/server/src/twobrain_rec_server/cabinet/web.py` at 2125 lines. Adjacent
files are inputs/validation references, not intended cleanup targets:
`cabinet/rendering.py`, `cabinet/view_models.py`, `cabinet/egress.py`,
`api/cabinet.py`, and cabinet tests.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Before Phase 0**: PASS.

- Spec-driven delivery: PASS. 073 has its own slice and tasks.
- Product behavior preservation: PASS. Spec forbids UX/auth/deletion/egress
  semantic changes.
- Privacy/security gates: PASS. CSRF, auth/session, tenant scope, and no-secret
  checks are explicit validation requirements.
- Capture boundary: PASS. 073 does not touch capture code.
- Desktop/server trust boundary: PASS. Desktop embedded routes are preserved;
  route policy semantics are not changed.
- Release discipline: PASS. No production deploy.
- Ponytail form: PASS. Minimal split, no new dependency, no broad rewrite.

**After Phase 1 design**: PASS. Research, contracts, and quickstart keep the
diff limited to cabinet web route organization and focused tests.

## Validation Plan

Run before implementation completion:

```sh
uv --project apps/server run --extra dev pytest -q \
  apps/server/tests/contract/test_cabinet_contract.py \
  apps/server/tests/contract/test_cabinet_csrf_contract.py \
  apps/server/tests/contract/test_cabinet_no_secret_content_egress.py \
  apps/server/tests/integration/test_cabinet_csrf.py \
  apps/server/tests/integration/test_cabinet_hx_fragments.py \
  apps/server/tests/integration/test_cabinet_meeting_detail.py \
  apps/server/tests/integration/test_cabinet_meeting_list.py \
  apps/server/tests/integration/test_cabinet_web_access_states.py \
  apps/server/tests/integration/test_meeting_deletion_workflow.py \
  apps/server/tests/integration/test_web_owner_session_context.py \
  apps/server/tests/unit/test_cabinet_web_shell.py
git diff --check
```

If the split touches calendar settings routes, also run:

```sh
uv --project apps/server run --extra dev pytest -q \
  apps/server/tests/contract/test_calendar_no_secret_content_egress.py \
  apps/server/tests/integration/test_calendar_deletion_lifecycle.py
```

Broader CI (`infra/scripts/ci-local.sh`) is recommended before final PR if the
focused gates pass and runtime files changed. Production deploy is excluded.

## Project Structure

### Documentation (this feature)

```text
specs/073-cabinet-web-split/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/src/twobrain_rec_server/cabinet/
├── web.py                  # Public router import remains stable
├── rendering.py            # Read-only dependency for 073 unless required import move
├── templates.py            # Read-only dependency
├── view_models.py          # Read-only dependency
└── web_routes/             # New route-family modules if implementation uses module split

apps/server/tests/
├── contract/
├── integration/
└── unit/
```

**Structure Decision**: Use small route-family modules under the cabinet package
only if they reduce `web.py` without duplicating helpers. Keep `web.py` as a
thin public assembly surface exporting `router`.

## Complexity Tracking

No constitution violations.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
