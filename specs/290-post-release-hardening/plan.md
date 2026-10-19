# Implementation Plan: Эксплуатационные хвосты выпуска

**Branch**: `290-post-release-hardening` | **Date**: 2026-10-17 | **Spec**: [spec.md](spec.md)

## Summary

Сохранить полный объём #6501. Первый самостоятельный срез заменяет Actions
Node20 поддерживаемыми Node24 actions, сохраняя реальные проверки и формат
доказательств. Судьба stash и четыре эксплуатационных сценария проверяются
отдельно; они не закрываются обновлением YAML.

## Technical Context

- Language/Version: YAML, Bash, Python 3.13, Swift 6.0.3; Node приложения 22.22.3.
- Dependencies: существующие GitHub-hosted runners, pytest/PyYAML; новых нет.
- Storage: новые данные продукта не создаются; только безопасные метаданные.
- Risk / Validation Lane: **high-risk-product**, инфраструктура/backup/deploy.
- Release Gate: первый срез без deploy; implementation commit после согласия,
  merge после трёх exact-SHA checks по действующему общему согласию; будущий выпуск —
  один Full нового frozen SHA, dry-run CD и отдельное разрешение execute.
- Platforms: Ubuntu hosted, macos-14; server Linux только на позднем этапе.
- Scope: 6 workflow, 2 валидатора, 3 существующих файла тестов, changelog fragment.
- Performance: без нового повторного этапа CI, кэш изолирован по compiler build.
- Constraints: не менять обязательные имена, trust boundary, permissions,
  scope, concurrency, SHA/base/run/attempt, сроки хранения и ZIP receipts.

## Constitution Check

До Phase 0: принципы I–II — capture и consent не меняются; III–IV — секреты,
данные встреч, deletion и обязательные backups сохраняются; V — выпуск здесь
не выполняется; VI — clarify/checklist/analyze/task sync до кода; VII — UI
не меняется. Конституция 7.1.0, нарушений/исключений нет.
После Phase 1: те же ограничения сохранены. Независимый reviewer проверяет
качество требований, не подтверждает исполнение production или hosted CI.

## Design

Решения и точные commit pins — [research.md](research.md). Все action versions
закрепить commit SHA с комментарием версии. Сохранить `persist-credentials:false`,
trusted workflow ref и `python3 -I`. Для setup-node явно отключить новый
автоматический npm cache; upload оставляет `archive:true` и прежние имена;
download оставляет распаковку и строгую проверку digest.

В трёх native workflows заменить setup-swift на одинаковый короткий Bash-шаг:
зафиксировать SDK/xcode-select до выбора, проверить абсолютные swift/swiftc из
Xcode16.2, status команд и точную semantic version 6.0.3, проверить неизменность
SDK после PATH выбора; только затем добавить bin в GITHUB_PATH. Не менять
DEVELOPER_DIR, xcode-select или SDKROOT. Apple compiler build отличается от
Swift.org — это явное техническое изменение в рамках Swift6.0.3, поэтому
новый namespace key **и** restore-prefix кэша. Совместимость подтвердит настоящий
hosted build/XCTest/ContractValidation; локальная подмена toolchain этого не доказывает.

macos-14 отключается 2026-11-02; до этого есть временные отключения. Этот срез
устраняет Node20, но не доказывает работу на новом image. До вывода macos-14
нужна отдельная миграция с исследованием доступности Swift6.0.3/SDK и актуальным
clarify/review. Нельзя молча заменить runner или compiler в этом срезе.

US2: сначала закрытая read-only инвентаризация неизменяемого stash OID,
включая index и untracked parent, без apply/pop/drop. Сопоставить с пятью
файлами чужой работы из release-v2026.10.16.6 и действующим владельцем.
Не проектировать параллельную ротацию до этой проверки. Перенос полезной
части после уточнения design/review, локальной проверки и согласия на commit.
Удаление stash/снимка/сохранённой копии только с отдельным согласием.

US3: переиспользовать worker/service/Range/restore проверки из research.
Не вызывать inventory функцию как read-only: она пишет и делает commit.
Сначала конкретная процедура каждого сценария и rollback/cleanup на синтетике,
затем isolated проверки, затем согласие на точные production действия.
Модель deployment.py требует все четыре pass; соответствие поля
normalization_cleanup_result → cleanup_result задаётся явно. Ни healthy poller,
ни пустой inventory, ни старое evidence не заменяют исполнение сценария.

## Validation Plan

1. Предварительный независимый requirements review и analyze: 0 critical/high.
2. Исполнимые положительные и отрицательные проверки native выбора в существующем
   workflow harness: missing binary, 6.0.31, command failure с valid stdout,
   смена SDK, неизменный GITHUB_PATH при отказе.
3. Existing governance/full workflow validators, workflow/metadata contracts,
   actionlint, process/governance/changelog и git diff --check.
4. Независимое ревью diff; проверенный commit по действующему общему разрешению только после PASS.
5. Exact PR SHA: governance-fast, macos-pr и pr-metadata через общий validator.
6. US2/US3 — собственные условия приёмки в quickstart; сервер не меняется
   ради доказательств первого CI среза.

## Project Structure

Документы: spec.md, plan.md, research.md, data-model.md, quickstart.md,
checklists/infra.md, tasks.md. Новый публичный API не добавляется; contracts/
не требуется, существующие ZIP и deployment-result contracts сохраняются.
Код: `.github/workflows/`, `scripts/validate-*-workflow.py`, существующие
workflow tests; `changes/unreleased/F290.yaml`.
Поздний US2/US3 уточняет owned paths после инвентаризации, до изменения кода.

## Complexity Tracking

Новых служб, зависимостей, общего framework и обходных режимов нет.
