# Implementation Plan: Контекстная ссылка на приложение на экране входа

**Branch**: `codex/161-graf-ux-regressions` | **Date**: 2026-08-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/166-login-download-cta/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Разделить CTA скачивания на экране входа по уже существующему безопасному
целевому маршруту: обычный web login показывает одну заметную ссылку на
`/download` вне карточки авторизации, embedded login с `/desktop/...` не
показывает её совсем. Auth routes, redirect validation и публичные download
поверхности остаются без изменений.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.13, Jinja2 templates, vanilla CSS

**Primary Dependencies**: Existing FastAPI cabinet rendering, Jinja2, existing cabinet stylesheet; no new dependency

**Storage**: N/A; surface context is derived per request and is not persisted

**Testing**: Focused pytest unit/integration render checks, template/source assertions, in-app browser visual pass, embedded macOS visual pass

**Risk / Validation Lane**: `high-risk-feature` — auth is a protected surface and the change affects both browser and embedded UX; no credentials, session semantics, or redirect policy change

**Release Gate**: `no deploy` — this is one reviewed release-train slice; production rollout waits for the combined release candidate

**Target Platform**: Modern browser and embedded macOS WebView cabinet

**Project Type**: Server-rendered web cabinet shared by browser and embedded desktop app

**Performance Goals**: No additional request, client script, layout observer, or persistent state; one presentation decision during render

**Constraints**: Reuse normalized safe `next`; preserve auth error, invitation, provider and legal-copy behavior; keep the CTA keyboard-accessible and non-overlapping from 320 px upward

**Scale/Scope**: One auth template, one auth rendering helper, shared auth CSS, focused unit/integration contracts, and two visual surfaces

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Capture-First MVP Integrity: PASS — no recording, audio, permission or playback behavior changes.
- Visible Consent And User Control: PASS — no capture control or recording indicator is touched.
- Plaintext Observability For Internal MVP: PASS — no meeting content, external egress, telemetry or secret is introduced.
- Deletion Truth And Lifecycle Accounting: PASS — no meeting artifact, retention or deletion behavior changes.
- Public macOS Distribution And Update Integrity: PASS for this slice — no package, signing, update or release artifact is changed.
- UI/accessibility/clean-room: PASS — CTA keeps original GRAF visual language, has an accessible name/focus state, and is checked on browser and embedded surfaces.
- Spec-driven delivery: PASS — this high-risk auth UX slice has specify, clarify, plan, UX/security checklists, tasks, analyze and focused evidence.

## Validation Plan

1. Run focused unit and integration render tests for web and `/desktop/...`
   login contexts, including auth error responses.
2. Run source/template contract checks, `node --check` for unchanged shared
   client assets where the repository gate expects it, and `git diff --check`.
3. Review the web login visually in the in-app browser at wide and narrow
   widths, with keyboard focus and auth-error copy.
4. Review the embedded login visually with Computer Use at wide and narrow
   widths, confirming the CTA is absent and auth controls remain readable.
5. Run `infra/scripts/ci-local.sh --fast` once after the complete slice. No
   production deploy, CD execution or full release gate is required until the
   combined release candidate is assembled.

## Project Structure

### Documentation (this feature)

```text
specs/166-login-download-cta/
├── spec.md
├── clarify.md
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
apps/server/src/twobrain_rec_server/cabinet/
├── auth_rendering.py
├── templates/cabinet/auth/login.html
└── static/cabinet/cabinet.css

apps/server/tests/
├── unit/test_cabinet_web_shell.py
└── integration/test_web_owner_session_context.py

CHANGELOG.md
```

**Structure Decision**: Reuse the shared server-rendered login template and
existing normalized `next` value. The web/embedded choice is a presentation
boolean passed to the template; no new route, cookie, header, storage,
JavaScript or component layer is added.

## Complexity Tracking

No constitution violations. Ponytail ceiling: derive one boolean from the
already-normalized path, render one web-only CTA, and scope the new CSS to the
auth page root; do not add client detection, persistence, analytics or a new
auth surface.
