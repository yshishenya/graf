# Feature Specification: Cabinet Web Split

**Feature Branch**: `codex/073-cabinet-web-split`

**Created**: 2026-07-01

**Status**: Draft

**Input**: User approved the next 072 roadmap step: carefully execute RB-072-01 as a product-improving, behavior-preserving split of the oversized server-rendered cabinet web router.

## Clarifications

### Session 2026-07-01

- Lane: significant architecture / high-risk behavior-preserving refactor because the cabinet web router touches auth/session, CSRF, deletion/reporting, calendar settings, desktop WebView routes, and meeting review pages.
- Scope: split the cabinet web routing layer into smaller, readable route families while preserving every existing public route, response type, status code, redirect target, auth/session behavior, CSRF requirement, HX fragment behavior, and desktop embedded route.
- Safety rule: do not change product behavior, templates, view-model semantics, egress/download/export behavior, deletion/retention semantics, auth provider semantics, database models, migrations, dependencies, or deployment scripts.
- Ponytail rule: reuse the existing FastAPI router, dependencies, helpers, renderers, tests, and file patterns; add only the smallest module boundary needed to reduce `cabinet/web.py` responsibility.
- Release rule: no production deploy for 073 unless separately requested after merge readiness.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Maintainer Can Review Cabinet Routes By Responsibility (Priority: P1)

A maintainer can open the cabinet web layer and find browser auth, meeting pages, calendar settings, desktop embedded pages, deletion request/reporting, and static icon routes in separate responsibility groups instead of one long file.

**Why this priority**: The 072 audit identified `cabinet/web.py` as the first safe split candidate. Smaller route families improve future product work without changing user behavior.

**Independent Test**: Review the cabinet web module structure and confirm each route family has a clear owner while `twobrain_rec_server.cabinet.web.router` remains the public router imported by `main.py`.

**Acceptance Scenarios**:

1. **Given** a maintainer needs to change a meeting detail route, **When** they inspect the cabinet web layer, **Then** the meeting route code is separated from login/signup/provider auth and calendar settings code.
2. **Given** `main.py` imports `twobrain_rec_server.cabinet.web.router`, **When** the app starts, **Then** the same cabinet web router is still available from that import path.
3. **Given** future work needs a smaller PR boundary, **When** it uses the new route grouping, **Then** it can touch one family without scanning the entire previous `web.py` file.

---

### User Story 2 - Existing Browser And Desktop Cabinet Behavior Stays The Same (Priority: P1)

A user or desktop shell sees the same cabinet pages, redirects, fragments, auth requirements, and deletion/reporting behavior after the split.

**Why this priority**: The split is only valuable if product behavior is preserved. Cabinet pages are user-facing and include security/privacy boundaries.

**Independent Test**: Run focused cabinet web, CSRF, HX fragment, owner-session, deletion/reporting, and no-secret egress tests before and after the split.

**Acceptance Scenarios**:

1. **Given** existing browser routes for login, signup, meetings, settings, calendar settings, and deletion reports, **When** tests request those routes, **Then** response status, redirect behavior, and rendered safety properties remain unchanged.
2. **Given** desktop embedded routes under `/desktop/...`, **When** tests request those routes, **Then** the same embedded-safe pages and fragments are returned.
3. **Given** HX requests for cabinet fragments or deletion feedback, **When** the route family is split, **Then** fragment responses continue to match the existing contract.

---

### User Story 3 - Security And Privacy Boundaries Are Not Weakened (Priority: P1)

An owner can trust that auth/session, CSRF, no-secret content egress, deletion/retention truth, and desktop WebView boundaries are preserved by the refactor.

**Why this priority**: This route layer sits across the highest-risk cabinet trust boundaries. A prettier file layout is not worth a weaker product.

**Independent Test**: Run security/privacy-focused cabinet tests and verify no route loses its existing dependency, CSRF guard, tenant scope, or no-secret output expectation.

**Acceptance Scenarios**:

1. **Given** a POST route currently requires web CSRF, **When** the route is moved, **Then** the same CSRF dependency still protects it.
2. **Given** a route depends on authenticated principal or tenant scope, **When** the route is moved, **Then** that dependency remains intact.
3. **Given** no-secret cabinet response tests exist, **When** the split is complete, **Then** they still pass without weakening assertions.

### Edge Cases

- Route registration order must not change in a way that changes path matching, especially paired browser and desktop routes.
- Helper functions shared by multiple route families must have one owner and must not be duplicated across modules.
- Browser auth helper movement must not alter cookie names, callback state handling, workspace resolution, or provider selection.
- Calendar POST route movement must not drop CSRF or audit event behavior.
- Deletion request/report route movement must not alter bounded deletion truth or local purge expectations.
- Tests may import `cabinet.web.router`; that import path must remain stable.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The refactor MUST preserve `twobrain_rec_server.cabinet.web.router` as the public cabinet web router import used by `main.py`.
- **FR-002**: The refactor MUST split the current cabinet web route responsibilities into smaller route-family modules or equivalent local boundaries.
- **FR-003**: The refactor MUST preserve every existing cabinet web route path, HTTP method, response class, include-in-schema behavior, redirect target, and status code.
- **FR-004**: The refactor MUST preserve browser login, signup, email verification, and provider-start behavior without changing auth/session semantics.
- **FR-005**: The refactor MUST preserve browser meeting list/detail and settings page behavior.
- **FR-006**: The refactor MUST preserve calendar settings, provider connect/result, source selection, sync, disconnect, and preferences behavior.
- **FR-007**: The refactor MUST preserve desktop embedded meeting/settings/calendar/deletion report route behavior under existing `/desktop/...` paths.
- **FR-008**: The refactor MUST preserve meeting deletion request/report behavior and deletion/retention truth.
- **FR-009**: The refactor MUST preserve all existing CSRF, authenticated principal, tenant scope, storage, and database dependency requirements.
- **FR-010**: The refactor MUST preserve HX request detection and fragment rendering behavior.
- **FR-011**: The refactor MUST avoid changing templates, view-model semantics, egress/download/export semantics, auth provider semantics, database models, migrations, dependencies, infra scripts, or release files.
- **FR-012**: The implementation MUST reuse existing helpers where practical and avoid duplicate route logic.
- **FR-013**: The implementation MUST include focused validation evidence before merge and MUST NOT run production deploy for this slice.
- **FR-014**: If a desired cleanup would change behavior or cross auth/deletion/egress/capture/deploy boundaries, it MUST be deferred to a separate Spec Kit slice.

### Key Entities *(include if feature involves data)*

- **Cabinet Web Router**: The public FastAPI router exported from `twobrain_rec_server.cabinet.web`.
- **Route Family**: A responsibility group such as static icons, browser auth, browser meetings/settings, calendar settings, desktop embedded pages, or deletion routes.
- **Shared Web Dependency**: Existing FastAPI dependency or helper for tenant scope, principal, CSRF, database session, storage, query/form parsing, or HX detection.
- **Route Contract**: Existing externally visible path/method/status/redirect/rendering behavior covered by tests.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `apps/server/src/twobrain_rec_server/cabinet/web.py` is reduced from a monolithic route implementation into a small public router assembly/import surface while preserving the existing import path.
- **SC-002**: Focused cabinet web tests pass after the split, including cabinet route contracts, CSRF, HX fragments, meeting list/detail, owner session, deletion/reporting, and no-secret content checks.
- **SC-003**: No runtime product files outside the cabinet web route split and required imports/tests are changed.
- **SC-004**: No new runtime dependency, migration, deploy script change, or production deploy is introduced.
- **SC-005**: A reviewer can identify which route family owns browser auth, browser pages, calendar settings, desktop embedded pages, and deletion routes without reading one 2000-line file.

## Assumptions

- 073 starts from merged 072 audit on `origin/master`.
- Existing tests are the primary regression evidence; new tests are added only if an uncovered moved boundary needs a minimal check.
- The first split should target route ownership, not templates, view models, egress helpers, auth internals, or deletion service internals.
- If route extraction reveals behavior coupling that cannot be preserved with a small move, the task stops and records a new risky finding instead of forcing a larger rewrite.
