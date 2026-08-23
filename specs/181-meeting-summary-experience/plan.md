# Implementation Plan: Полезные итоги встреч

**Branch**: `181-meeting-summary-experience` | **Date**: 2026-08-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/181-meeting-summary-experience/spec.md`

## Summary

GRAF перестаёт публиковать deterministic extractive baseline как готовые итоги новой встречи. Первый строго проверенный автоматический AI-вариант становится исходным принятым результатом только когда у встречи ещё нет принятой версии; все ручные обновления и смены формата по-прежнему проходят через безопасный preview-before-replace.

Девять встроенных форматов получают разные, версионированные смысловые контракты поверх существующего Langfuse/LiteLLM/Temporal пути. Интерфейс показывает назначение формата, честное состояние первоначальной генерации и понятный lifecycle кандидата. Качество доказывается на синтетическом наборе и отдельно разрешённой локальной выборке реальных встреч без публикации содержимого.

## Technical Context

**Language/Version**: Python 3.12; server-rendered HTML/Jinja; plain JavaScript/CSS; Swift 6/macOS shell без нового native summary UI

**Primary Dependencies**: FastAPI, SQLAlchemy async, PostgreSQL, Temporal, Langfuse Prompt Config, owner-controlled LiteLLM, Jinja/HTMX cabinet shell

**Storage**: существующие PostgreSQL `meetings`, `meeting_outcome_sets`, `meeting_outcome_items`, `meeting_outcome_generation_attempts`, dispatch intents и Generation Call ledger; новая миграция не планируется

**Testing**: pytest unit/contract/integration через disposable PostgreSQL runner; browser checks существующего cabinet surface; Swift route/zoom regressions для embedded parity

**Risk / Validation Lane**: high-risk feature — AI, приватные транскрипты, accepted-result truth, user-facing degraded states и основной post-meeting workflow

**Release Gate**: no deploy. Реализация и локальная проверка разрешены; Langfuse production promotion, commit, PR, release и production deploy требуют отдельных gates и явного одобрения

**Target Platform**: Linux server/web cabinet и тот же cabinet внутри установленного macOS `GRAF.app`

**Project Type**: server-owned web application embedded into a native macOS shell

**Performance Goals**: 90% встреч получают AI-итоги или конкретное честное состояние не позднее 15 минут после готовности транскрипта; UI остаётся отзывчивым, polling bounded текущими пределами

**Constraints**: без эвристического пользовательского fallback; без прямого provider call; exact source refs; no invented owners/dates/decisions; private content только в одобренных operator-controlled контурах; evidence и git metadata-only

**Scale/Scope**: девять встроенных форматов, personal formats, initial generation, manual regeneration, candidate preview/accept/reject, browser/embedded parity, synthetic and authorized-private evaluation

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Capture-first и visible-recording contracts не затрагиваются.
- AI egress остаётся только через allowlisted LiteLLM; Langfuse остаётся единственным editable prompt/config authority.
- Полный transcript/model content остаётся в одобренных Langfuse, Generation Call и Temporal boundaries; обычные logs, screenshots, issues и committed evidence остаются metadata-only.
- Accepted-result truth сохраняется: автоматическое принятие разрешено только для первого строго проверенного system candidate при отсутствии принятого результата; ручная регенерация никогда не перезаписывает accepted truth молча.
- RLS, deletion epoch, source revision, access и immutable lineage fences переиспользуются без ослабления.
- UX проходит keyboard, focus, live-region, zoom, localization и clean-room/brand-distance gates.
- Новых внешних зависимостей, provider routes, migrations или privileged boundaries нет.

## Validation Plan

1. RED: доказать, что deterministic baseline больше не публикуется для новой revision-scoped встречи и первый automatic AI result остаётся candidate до явного принятия пользователем.
2. Prompt contracts: все девять форматов имеют разные required emphasis, exclusions и output guidance; strict schema/source validation сохраняется.
3. Lifecycle/API: initial pending/error, manual format, refresh, preview, accept, reject, retry, stale/expired/deletion/source-change и idempotency.
4. UI contract: описания форматов в quick picker/full dialog, честная initial state, controls скрыты/disabled только согласно реальной доступности, status text отделён от action buttons.
5. PostgreSQL focused suite через `bash apps/server/scripts/run_local_postgres_tests.sh`.
6. Synthetic browser matrix: all formats, all buttons, keyboard, focus, 390px/1280px, 200% zoom, web and embedded routes.
7. Authorized-private local evaluation: только агрегированные scores/counts/hashes; без transcript/output text в git или ответах.
8. `infra/scripts/ci-local.sh --fast` перед closeout/PR. Full lane, prompt promotion, release and deploy are separate approved gates.

## Project Structure

### Documentation (this feature)

```text
specs/181-meeting-summary-experience/
├── spec.md
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── ux-audit.md
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)
```text
apps/server/src/twobrain_rec_server/
├── outcomes/
│   ├── ai_service.py
│   ├── generator.py
│   ├── prompts.py
│   ├── service.py
│   └── templates.py
├── cli/langfuse_prompts.py
├── api/cabinet.py
└── cabinet/
    ├── rendering.py
    ├── templates/cabinet/pages/meeting_detail_content.html
    └── static/cabinet/{cabinet.js,cabinet.css}

apps/server/tests/
├── contract/
├── integration/
└── unit/
```

**Structure Decision**: изменить существующий server-owned outcome path и cabinet UI; не добавлять новый сервис, UI framework, prompt store, database entity или native macOS summary implementation.

## Complexity Tracking

Нет нарушений constitution и нет оправданной дополнительной сложности.
