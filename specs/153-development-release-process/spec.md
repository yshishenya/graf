# Feature Specification: Процесс от разработки до релиза

**Feature Branch**: `151-settings-product-surface`

**Created**: 2026-08-16

**Status**: Ready for implementation

**Input**: User description: «Записать правила CI и выстроить общий процесс разработки, редких релизов и выкатывания»

## User Scenarios & Testing

### User Story 1 - Быстрая ежедневная разработка (Priority: P1)

Разработчик хочет получать быстрый сигнал после изменения, не тратя время на
полный CI после каждого маленького шага.

**Why this priority**: Это основной ежедневный цикл и источник быстрой обратной
связи.

**Independent Test**: По инструкции разработчик может выбрать focused check или
fast lane и понять, что результат не является разрешением на production.

**Acceptance Scenarios**:

1. **Given** изменён один локальный путь, **When** разработчик проверяет его,
   **Then** инструкция направляет его на focused checks.
2. **Given** готова фича или PR, **When** разработчик закрывает локальную
   проверку, **Then** инструкция требует fast lane и записи результата.

### User Story 2 - Редкий и воспроизводимый релиз (Priority: P1)

Ответственный за релиз хочет накопить несколько изменений, один раз проверить
кандидат полным CI и выкатить ровно проверенный commit.

**Why this priority**: Это связывает редкую частоту выкатывания с доказуемой
надёжностью, а не с плавающим состоянием ветки.

**Independent Test**: По инструкции можно пройти путь от release candidate до
production dry-run и определить, какой SHA является источником evidence.

**Acceptance Scenarios**:

1. **Given** полный CI завершился успешно для SHA X, **When** появился новый
   commit, **Then** результат для SHA X считается устаревшим.
2. **Given** выбран release candidate, **When** выполняется production deploy,
   **Then** CD повторяет full gate на pinned SHA до backup и rollout.
3. **Given** production deploy ещё не одобрен, **When** запускается dry-run,
   **Then** он показывает план без выполнения rollout.

### Edge Cases

- Полный CI прерван или завершился без итогового pass: кандидат не считается
  проверенным.
- После полного CI изменены код, конфигурация, release metadata или lockfile:
  полный CI запускается заново.
- Рабочее дерево грязное, ветка не совпадает или SHA не совпадает с remote:
  production execute блокируется.
- `--skip-local-ci` используется только как явно одобренное incident-исключение
  с записанным риском.

## Requirements

### Functional Requirements

- **FR-001**: Правила MUST разделять focused checks, fast lane, full lane и
  production deploy gate.
- **FR-002**: Правила MUST требовать fast lane перед PR/closeout для значимых и
  высокорисковых изменений.
- **FR-003**: Правила MUST запрещать считать fast lane или focused checks полным
  CI в release evidence.
- **FR-004**: Правила MUST ограничивать ручной full CI release candidate,
  ранней широкой диагностикой или обязательным production execute gate.
- **FR-005**: Правила MUST привязывать результат полного CI и deployment evidence
  к точному SHA.
- **FR-006**: Правила MUST считать full-CI evidence недействительным после любого
  изменения кандидата.
- **FR-007**: Правила MUST требовать CD dry-run до production execute и явное
  одобрение перед execute.
- **FR-008**: Правила MUST описывать post-deploy smoke, rollback и metadata-only
  closeout evidence.
- **FR-009**: Правила MUST сохранять действующие требования notarization, signing,
  release notes и CalVer для публичного macOS-релиза.
- **FR-010**: Правила MUST требовать готовить release metadata до финального
  full CI, чтобы проверялся именно поставляемый кандидат.

### Key Entities

- **Validation result**: команда, режим, точный SHA, время, итог и область
  проверки.
- **Release candidate**: накопленный и неизменяемый commit, прошедший
  release-level validation.
- **Deployment gate**: последовательность dry-run, approval, full CI, backup,
  rollout, smoke и rollback evidence.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Разработчик может выбрать правильную проверку для локального шага,
  PR или релиза без дополнительных устных правил.
- **SC-002**: Каждый production deploy имеет evidence полного CI для того же
  SHA, который был выкатан.
- **SC-003**: Ни один новый commit после полного CI не может быть описан как
  проверенный без повторного full run.
- **SC-004**: Production execute не начинается до dry-run и явного approval.
- **SC-005**: Release closeout содержит SHA, full-CI result, smoke и rollback
  status без raw meeting data или secrets.

## Assumptions

- GitHub Actions остаются выключенными; автор отвечает за запуск и запись
  локального validation lane.
- Выкатывание происходит пакетами и не обязано выполняться после каждого PR.
- Существующие `ci-local.sh`, `cd-remote.sh`, release и macOS notarization
  gates остаются каноническими командами.
- Изменение не включает включение remote CI, новый orchestrator или изменение
  runtime-поведения продукта.

## Out of Scope

- Включение GitHub Actions или разработка новой CI-платформы.
- Изменение состава тестов и deploy-скриптов.
- Автоматическое определение частоты релизов.
- Ослабление security, signing, notarization, backup, smoke или rollback gates.
