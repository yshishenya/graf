# Implementation Plan: F243 cabinet audit remediation

**Branch**: `codex/243-cabinet-audit-remediation` | **Date**: 2026-09-06
**Spec**: [spec.md](spec.md)

## Summary

Исправить общие причины подтверждённых ошибок кабинета. Использовать текущие
NSAlert, route policy, Jinja, CSS tokens и JS. Удалить только неиспользуемый каталог.

## Technical Context

- Python3.12+, Swift6, JavaScript, Jinja/CSS; существующие FastAPI, AppKit/WebKit.
- Storage: существующий PostgreSQL, без миграций или смены API.
- Testing: pytest, Node, XCTest, Chrome/WebKit; macOS14.5+.
- **Risk / Validation Lane**: high-risk-feature — auth/deletion, native trust
  boundary, shared UI, accessibility/localization.
- **Release Gate**: no deploy; exact-SHA GitHub `governance-fast` for PR.
- Performance: bounded layout work on existing events, no polling/network for overlays.
- Constraints: no new dependencies; synthetic data, metadata-only evidence;
  no root governance edits, capture controls/auth/RLS remain unchanged.

## Constitution Check

Before Phase0: PASS — capture/visibility unchanged; server remains authority;
confirm is not authorization; exact external handoff; truthful deletion copy;
no competitor assets/private content/public binary publication.
After Phase1: PASS — independent requirements review on 2026-09-06:
security 5/5, UX 6/6; contracts preserve auth/tenant/capture boundaries.
Post-review analyze: all 10 FRs covered by 13 owned tasks; no critical/high
inconsistencies. Theme ownership corrected below; implementation QA still pending.

## Validation Plan

See [quickstart.md](quickstart.md): Python renderer/contract and database settings
tests, executable JS, actual Swift route/confirm tests, browser matrix, hygiene.
Full CI, notarization and installed production smoke remain release gates.

## Project Structure

- `apps/macos/RecApp/Sources/Cabinet/` and `apps/macos/Shared/Tests/`.
- `apps/server/src/twobrain_rec_server/cabinet/`: templates/view models/CSS/JS.
- `apps/server/src/twobrain_rec_server/admin/`: role/status presentation.
- `apps/server/tests/{unit,contract,integration,fixtures}/`: regressions.
- `specs/243-cabinet-audit-remediation/`: scoped artifacts and evidence.
- `changes/unreleased/F243.yaml`: release fragment.

## Implementation sequence

1. Native confirmation/route regressions and fixes.
2. Shared interactive UI, focus and truthful copy.
3. Retire unused macros/selectors; meaningful production privacy coverage.
4. Integrate coordinated fixes, validate, review, converge, commit/push and PR.

## Coordination

F240 owns global theme tokens, light surfaces and explicit-dark dialogs.
F244 owns short upload scroll, pinned320px and upload accessible name.
F243 does not duplicate those rules. F242 owns theme partial
save, valueless autosave attributes and profile transmission.
F243 owns tooltip/submenu/calendar border, native and copy/catalog changes.
Exact integration SHA/PRs are required for combined visual acceptance. No merge
or deploy is authorized by coordination.
