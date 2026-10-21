# Implementation Plan: CI merge queue и provenance release train

**Branch**: `codex/227-ci-merge-queue-release-train` | **Date**: 2026-08-31

**Spec**: [spec.md](spec.md)

**Umbrella issue**: [#6207](https://github.com/yshishenya/graf/issues/6207)

## Risk / Validation Lane

`significant-feature`: shared CI, GitHub event identity, release provenance and
branch protection. Required path:
`specify → clarify → plan → checklist → tasks → analyze → taskstoissues →
implement → converge → exact-SHA validation`.

## Constitution Check

- Principle VI is preserved through testable requirements, explicit lane,
  checklist, task traceability and exact-SHA gates.
- Principle V is preserved: no signing/notarization or public app release gate
  is weakened; stale evidence is rejected.
- No capture, privacy, auth, storage, Temporal behavior or production data is
  changed.

## Architecture

```text
GitHub event
  ├─ pull_request.head.sha
  ├─ merge_group.head_sha + group/pr mapping
  └─ manual exact SHA
          ↓
event identity resolver + canonical concurrency key
          ↓
exact checkout + target/base verification
          ↓
bounded CI + final cleanliness gate
          ↓
metadata-only CI receipt
          ↓
post-merge train manifest → one authoritative Full CI → immutable decision
```

## Components and Ownership

| Component | Responsibility | Location |
|---|---|---|
| Workflow contract | events, checkout, concurrency, receipt upload | `.github/workflows/governance-fast.yml` |
| Local lane | final cleanliness and receipt metadata | `infra/scripts/ci-local.sh`, `scripts/emit-ci-evidence.py` |
| Validators | event/receipt/train schema and stale checks | `scripts/validate-ci-evidence.py`, `infra/release/` |
| Release integration | train freeze/validate/decide provenance | `infra/scripts/release-candidate.sh` |
| PR contract | required feature/SHA/receipt fields | `.github/pull_request_template.md` |
| Generic extraction | portable schemas/templates/self-tests | `harness/` |
| Documentation | operator and agent runbooks | `docs/agent-guidance/` |

## Phases

1. Contract and schema fixtures.
2. Resolver, exact checkout and unified concurrency.
3. Final cleanliness and stale evidence validation.
4. Release-train manifest and candidate integration.
5. GitHub workflow, artifact receipt and operator documentation.
6. Convergence and exact-SHA validation; enforcement remains operator-owned
   after workflow merge.

## Data and Security Constraints

- Receipts contain metadata only: no logs, secrets, private absolute paths,
  audio, transcript text or signed URLs.
- Unknown event/SHA, missing base, superseded run, changed tree or mismatched
  candidate causes fail-closed `no-go`.
- Synthetic merge SHA and actual post-merge `master` SHA are separate fields.
- Full CI evidence is write-once per candidate; changed candidate means a new
  manifest.
- No production deploy or branch-protection mutation is performed here.

## Verification Strategy

- Unit/contract tests for resolver, schemas, concurrency keys and stale states.
- Workflow static validation and synthetic PR/manual/`merge_group` fixtures.
- Local fast lane on exact SHA.
- Release-candidate rehearsal with at least three synthetic PRs and one Full CI
  receipt.
- Generic harness self-test on supported Python versions.

## Текущий срез: T032–T033 (2026-10-17)

Lane: `Active Spec Kit slice`, область infrastructure/release provenance.
Сохраняются все исходные задачи и отдельные native merge-group gates.

1. T032: уточнить serial/native границы, происхождение synthetic, pinned Python
   matrix и воспроизводимые команды; независимое reviewer-owned ревью и анализ.
2. T033: в существующем `require_git_commit_relationship` обязать base быть
   предком source. Сохранить проверку существования трёх commits и все остальные
   exact-SHA/cleanliness/PR/Full CI gates. Не добавлять nullable-поле или новый
   режим. Проверить реальный serial commit-tree и несвязанную историю Git.

Владение кодом: `infra/scripts/release-candidate.sh` и существующий
`tests/governance/test_release_train.py`. Все вызовы общей функции прочитаны:
её вызывает train-freeze; release operator `scripts/release.sh` уже создаёт
корректный synthetic commit. Другие операции читают immutable manifest; менять
их формат и пересоздавать исторические записи не требуется. Pending F259
proof-binding меняет issue-closeout validator, пересечения кода нет.

Продуктовый код, GitHub protection, очередь, pinned harness package и действующий
runtime не меняются. Проверка проходит только в изолированном Git fixture;
GitHub PR proofs и Full CI там подставлены тестом и не считаются живой приёмкой.
После локальной проверки commit/PR и защищённое слияние выполняются по
действующему общему разрешению пользователя. Нужны три обязательные проверки
точного SHA/base. Выпуск отдельно.
Конституция после проектирования соблюдена: защиты усилены, выпуск не исполняется.


## Уточнение замечаний PR7678 — 21.10.2026

Текущая T033 должна защищать не только создание, но и потребление уже
замороженного train. Замечания4314292416/4314292430 требуют проверки
связи base→actual source в общей validate_train после проверки схемы:
её используют train-validate, candidate freeze, train-attest и decide --train. Существующий
require_git_commit_relationship переиспользуется, формат immutable
manifest/identity и проверки exact SHA/clean/PR/Full не меняются.
Git cat-file и merge-base этой проверки выполняются с --no-replace-objects,
чтобы локальная refs/replace graft не подменяла записанную историю.
Отдельные временные Git fixtures должны сначала воспроизвести acceptance
старого manifest и graft bypass, затем отказ всех потребителей без
новых файлов/перезаписи identity. Корректная serial история и существующая
положительная матрица остаются успешными. До реализации требуется
независимое reviewer-owned ревью этого уточнения; затем исходные RED,
минимальное общее исправление, focused suite и итоговое ревью.
T032/T033 остаются владельцами; исходные T001–T031 не закрываются.
