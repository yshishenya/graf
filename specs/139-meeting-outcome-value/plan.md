# Implementation Plan: meeting-outcome-value

**Branch**: `codex/139-meeting-outcome-value` | **Date**: 2026-08-04 |
**Spec**: [spec.md](./spec.md)

**Input**: Feature specification from
`/specs/139-meeting-outcome-value/spec.md`

## Summary

Сократить путь от пригодной расшифровки до проверяемой ценности: сразу оставить
доступным текущий быстрый результат, локально и идемпотентно поставить в очередь
один качественный вариант «Авто», затем показать его владельцу в компактной
структуре с owner/due и кликабельным источником до явного принятия. Усилить
versioned prompt/schema/eval gate, исправить speaker provenance и переиспользовать
существующие candidate, Temporal dispatch, player, share/export и access модели.

## Technical Context

**Language/Version**: Python 3.13 runtime, vanilla JavaScript, CSS,
Jinja/server-rendered HTML

**Primary Dependencies**: FastAPI, SQLAlchemy async, PostgreSQL, Temporal,
Langfuse Prompt Config, LiteLLM, existing cabinet renderer/player

**Storage**: existing PostgreSQL `MeetingOutcome*`, `DispatchIntent`,
`TranscriptSegment`, `DiarizationSegment`, `MeetingSpeakerName`; no migration
anticipated

**Testing**: focused pytest unit/contract/integration checks, synthetic prompt
regression, current-run in-app Browser desktop/mobile/state matrix,
`infra/scripts/ci-local.sh --fast`, release-candidate full lane

**Risk / Validation Lane**: `high-risk-feature`; меняются AI prompt policy,
automatic durable generation, evidence/acceptance и user-facing shared UX

**Release Gate**: implementation сначала `no deploy`; после validation и
отдельного user approval — PR/merge, full validation, prompt promotion gate,
production deploy и отдельная Developer ID public macOS release procedure

**Target Platform**: Linux server, web и macOS embedded cabinet; capture code не
меняется

**Project Type**: monorepo web service plus existing macOS client shell

**Performance Goals**: processing completion не ждёт Langfuse/LiteLLM/Temporal
network I/O; один local candidate/dispatch intent на source identity; ready UI
объясняет ценность за 30 секунд; existing 5-second dispatch reconciliation SLA
сохраняется

**Constraints**: никакого скрытого transcript truncation; candidate owner-only до
accept; accepted pointer не меняется автоматически; metadata-only committed
evidence; plaintext observability policy не меняется; no new service/framework/
dependency

**Scale/Scope**: один сквозной post-processing flow, десять outcome prompts,
три judge prompts, candidate preview, accepted/shared projections и bounded
meeting-list readiness; task hub/chat/integrations исключены

## Constitution Check

*GATE: PASS before Phase 0 and after Phase 1 design.*

- PASS — system-audio-first capture, visible indicator и one-action Stop не
  затрагиваются.
- PASS — desktop не получает AI/MediaScribe secrets и не делает content-bearing
  model calls; server продолжает использовать allowlisted LiteLLM.
- PASS — точный promoted Langfuse prompt/config pin сохраняется; изменённый
  prompt не получает `production` до held-out/operator gate.
- PASS — complete plaintext transcript/request/response retention в Langfuse,
  Generation Call и Temporal History сохраняется; committed evidence остаётся
  synthetic metadata-only.
- PASS — accepted Postgres pointer, deletion fence, owner-only candidate,
  viewer/share/export authorization и bounded deletion copy переиспользуются.
- PASS — clean-room GRAF IA и существующие tokens/components сохраняются;
  competitor assets/copy/layout не копируются.
- PASS — Ponytail: существующие candidate, dispatch, renderer, player и
  prompt-optimization механизмы покрывают задачу без нового сервиса, migration
  или UI framework.

Post-Phase-1 re-check: PASS. Contracts ниже не расширяют egress, retention,
capture или access boundaries.

## Design and Implementation

1. `processing/submit.py` создаёт automatic attempt/dispatch только при
   разрешённой policy после сохранения быстрого baseline. Выбор built-in default,
   meeting owner и expected accepted pointer проходит через существующий
   `create_summary_candidate`; model/network вызов остаётся maintenance/Temporal
   работой после commit.
2. `outcomes/prompts.py` и `cli/langfuse_prompts.py` вводят строгие определения,
   compactness, correction/dedup/unknown rules, `source_refs` 1..8, exact sequence
   и duplicate rejection. Изменённые prompts создаются без production label.
3. Existing transcript loader получает реальную overlap-based diarization и
   owner-renamed speaker name; AI и deterministic consumers reuse его. Если
   identity не подтверждена, label=`UNKNOWN`.
4. AI persistence обогащает model refs canonical timestamp/source role из pinned
   source, сохраняя stable generator version. Candidate preview API отдаёт
   structured refs; JS группирует локализованные primary/secondary sections и
   показывает owner/due/source до accept.
5. Accepted/source renderer создаёт action только при реальном destination;
   shared summary reuse тот же разрешённый read-only projection. Source jump
   переключает tab, seek и focus. Non-ready states агрегируются, list status
   различает transcript/outcome readiness.
6. Existing optimizer получает stronger judge instructions, worst-example
   held-out gate и runtime-aligned long-context fixture bound. Prompt promotion
   остаётся serialized/operator-controlled; exact numeric evidence не содержит
   content.

## Validation Plan

1. Focused Python checks: prompt/schema validator, speaker mapping, automatic
   candidate idempotency/dispatch, timestamp provenance, preview/share DTO,
   access/deletion races, list/degraded states.
2. Focused JS/HTML checks: localized candidate IA, source destination/focus,
   keyboard timeline, heading outline, 390 CSS px overflow.
3. Synthetic prompt gate: exact prompt/schema hashes, adversarial injection,
   unsupported decision/action/owner/due hard failures, beginning/middle/end
   long-context sentinels, worst-example held-out threshold.
4. Current-run Browser matrix: owner accepted/candidate, processing, blocked,
   no-player, full-viewer and summary-only at desktop and 390 CSS px; compare
   before/after screenshots without real content.
5. Before PR: `infra/scripts/ci-local.sh --fast`; before release/deploy:
   `infra/scripts/ci-local.sh --full` or manual GitHub full lane, then exact-SHA
   dry-run/execute. Prompt production promotion is an independent operator gate.

## Project Structure

### Documentation (this feature)

```text
specs/139-meeting-outcome-value/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── design-audit.md
├── contracts/meeting-outcome-value.md
├── checklists/
├── evidence/
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/src/twobrain_rec_server/
├── outcomes/{ai_service.py,prompts.py,prompt_optimization.py,service.py}
├── processing/submit.py
├── workflows/worker.py
├── api/{cabinet.py,schemas.py}
├── cabinet/
│   ├── {queries.py,view_models.py,rendering.py}
│   ├── web_routes/browser.py
│   ├── templates/cabinet/pages/
│   └── static/cabinet/{cabinet.js,cabinet.css}
└── cli/langfuse_prompts.py

apps/server/tests/{unit,contract,integration}/
docs/current-product-status.md
CHANGELOG.md
```

**Structure Decision**: изменить только существующий server/outcomes/cabinet
путь. Новый package допускается лишь если shared pure speaker/eval logic реально
сократит дубли; сначала переиспользуются текущие helpers.

## Complexity Tracking

No constitution violations. Skipped new AI service, schema migration, SPA,
notification system, task workspace, chat and hidden long-context chunking.
