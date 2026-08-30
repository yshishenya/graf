# Implementation Plan: Надёжный Spec Kit workflow

**Branch**: `212-spec-kit-workflow-hardening` | **Date**: 2026-08-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/212-spec-kit-workflow-hardening/spec.md`

## Summary

Мигрировать GRAF с legacy bootstrap lock schema 2 на воспроизводимое project-local состояние schema 3 для актуального Spec Kit, восстановить полный project workflow и добавить один focused governance check в fast CI. Проверка переиспользует штатный bootstrap `doctor` для integrity и самостоятельно защищает только GRAF-инварианты, которых upstream doctor не знает: полный порядок стадий, reviewer-owned custom checklists, границу сокращённого upstream workflow и managed local-state ignore rules.

## Technical Context

**Language/Version**: Python 3.9+ stdlib для focused guard; Bash orchestration существующего bootstrap/CI

**Primary Dependencies**: `specify-cli v1.0.1`, `speckit-bootstrap v0.9.7`, `github-issue-canon v0.3.2`, Git, существующие Spec Kit extensions

**Storage**: Tracked Markdown/YAML/JSON files и project-local `.agents/skills`; продуктовые хранилища не затрагиваются

**Testing**: Встроенный self-test focused guard с шестью negative classes, включая decoy вне canonical section; issue-canon command → frozen doctor regression и focused feature quickstart; ранее пройденный fast gate сохраняется как evidence, Full CI не запускается

**Risk / Validation Lane**: `significant-feature` — изменение governance, generated skills, CI gate и воспроизводимости инструментария; продуктовый runtime не меняется

**Release Gate**: `no deploy` — feature завершается PR-ready validation, без product release и production действий; macOS signing/notarization bootstrap assets — `N/A`, поскольку продуктовая сборка не меняется

**Target Platform**: macOS developer worktree; guard использует переносимый Python stdlib и существующий project bootstrap

**Project Type**: Monorepo governance/tooling maintenance

**Performance Goals**: Focused static guard завершается менее чем за 10 секунд без сети; bootstrap doctor использует frozen lock

**Constraints**: Не удалять legacy user-level skills; не менять master worktree; не устанавливать optional community extensions; не дублировать integrity checks bootstrap doctor

**Scale/Scope**: Один GRAF repository, 19 project-local Spec Kit skills, три установленных extensions, один upstream workflow и один локальный source checkout bootstrap

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **VI. Spec-Driven Delivery With Testable Gates — PASS**: выбран significant lane и выполняется полный Spec Kit cycle до implementation.
- **Repository hygiene — PASS**: изменения не содержат credentials, private meeting data, raw audio или secret paths.
- **Minimal implementation — PASS**: integrity делегируется существующему `speckit-bootstrap --doctor`; новый код защищает только project-specific invariants.
- **Tracking — PASS**: `tasks.md` остаётся implementation source of truth; issue sync выполняется до implementation.
- **Release safety — PASS**: bytecode-safe patch releases reusable tooling опубликованы с immutable tags/assets; GRAF product release/deploy исключены.

Post-design re-check: PASS — дизайн не вводит продуктовые, privacy, capture, auth, storage или deployment изменения и не ослабляет существующие gates.

## Validation Plan

1. До изменения: подтвердить latest upstream Spec Kit и stable bootstrap refs, чистый worktree и fast-forward возможность source checkout.
2. После bootstrap migration: проверить schema 3, immutable ref, project-local skill hashes, managed `.specify/.gitignore`; затем выполнить Python-backed issue-canon command и `speckit-bootstrap . --doctor --frozen`, убедившись в отсутствии `__pycache__`/`.pyc`.
3. Запустить focused guard в штатном режиме и его self-test с шестью отрицательными классами, включая неправильный порядок стадий и decoy вне canonical section.
4. Повторить bootstrap dry-run/apply и доказать отсутствие необъяснимого tracked drift.
5. Выполнить сценарии из `quickstart.md`, затем `infra/scripts/ci-local.sh --fast` как PR feedback gate.
6. Full CI не требуется: product runtime не менялся. Product release preparation, CD dry-run и deploy не выполнять.

## Project Structure

### Documentation (this feature)

```text
specs/212-spec-kit-workflow-hardening/
├── plan.md
├── research.md
├── quickstart.md
├── contracts/
│   └── governance-check.md
├── checklists/
│   ├── requirements.md
│   └── governance.md
└── tasks.md
```

### Source Code (repository root)

```text
AGENTS.md
CHANGELOG.md
docs/agent-guidance/spec-kit-flow.md
scripts/check_spec_kit_governance.py
infra/scripts/ci-local.sh
.specify/.gitignore
.specify/speckit-bootstrap.lock.json
.agents/skills/speckit-*/SKILL.md
```

**Structure Decision**: Не форкать и не переписывать upstream `speckit` workflow. Project-specific policy остаётся в `AGENTS.md` и `docs/agent-guidance/spec-kit-flow.md`; один Python stdlib guard подключается к существующему fast CI и проверяет, что bootstrap refresh не разрушил эти правила.

## Complexity Tracking

Конституционных нарушений и оправдываемых усложнений нет.
