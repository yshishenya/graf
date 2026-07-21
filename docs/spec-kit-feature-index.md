# Реестр Spec Kit и сверка документации

**Дата сверки**: 2026-07-21
**Проверяемая база**: `origin/master` (`7ea8afc5`)
**Lane**: docs-only reconciliation; код, production и tracker не изменялись.

## Как читать этот реестр

- `spec.md` фиксирует продуктовый intent и границы.
- `plan.md` фиксирует архитектурные решения и validation lane.
- `tasks.md` остаётся источником правды по реализации; открытый task не
  закрывается только потому, что рядом появился успешный тест.
- `validation/` содержит receipts и должен отличать локальную проверку,
  release proof и production proof.
- `docs/current-product-status.md` фиксирует принятую текущую продуктовую и
  runtime truth. Этот реестр связывает эти документы, но не заменяет их.
- Исторические локальные build/recording/worktree paths в evidence заменены
  на placeholders; literal `/Users/` в validation-командах оставлен только
  как detector pattern, а не как путь к реальному файлу.

## Инвентаризация

На текущем `master` найдено **97 spec-каталогов**, **97 `spec.md`** и **91
`tasks.md`**. Для 91 implementation slices есть `plan.md`, `tasks.md` и
`quickstart.md`. Полный artifact matrix такой:

| Артефакт | Найдено | Исключения |
| --- | ---: | --- |
| `spec.md` | 97 | нет |
| `plan.md` | 91 | six requirements-only specs below |
| `tasks.md` | 91 | six requirements-only specs below |
| `quickstart.md` | 91 | six requirements-only specs below |
| `research.md` | 90 | requirements-only specs и механический dead-code batch `075` |
| `data-model.md` | 87 | requirements-only specs и механические dead-code batches `075–078` |

Для `075` отсутствие `research.md`, а для `075–078` отсутствие `data-model.md`
намеренно: это delete/import-only cleanup без новых решений, сущностей,
миграций или storage границ; `plan.md`, `tasks.md`, `quickstart.md` и
validation остаются на месте.

Requirements-only намеренно оставлены без выдуманных plan/tasks:

| Spec | Состояние | Почему не добавляем искусственную реализацию |
| --- | --- | --- |
| `011-assisted-auto-recording` | specified, not planned | Будущая detect-and-ask функция; продуктовый baseline прямо оставляет её вне реализации. |
| `026`, `027`, `028`, `029` | requirements-only | Исторические/исследовательские требования без утверждённого implementation lane. |
| `101-streaming-egress-audit-semantics` | requirements-only, open | Требования к полноценной post-egress семантике сформулированы, но отдельный plan/tasks ещё не утверждён. |

Отсутствие `plan.md` или `tasks.md` в этих шести каталогах — намеренное
состояние, а не пробел, который нужно закрыть задним числом.

Отдельно не являются runtime implementation slices и поэтому не получают
искусственный статус «реализовано»:

| Spec | Текущее состояние | Следующий gate |
| --- | --- | --- |
| `072-deep-architecture-audit` | read-only audit artifacts готовы | audit review и отдельный refactor lane, если он будет утверждён |
| `086-desktop-upload-custody-architecture` | read-only custody architecture audit готов | отдельный implementation plan |
| `094-product-activation-analytics` | будущий backlog/discovery slice | новый SDD/Spec Kit цикл перед реализацией |

## Покрытие старых feature slices

Вне среза 096–118 каталог также покрывает исторические и текущие slices
`001–008`, `010–022`, `025–039`, `042–054`, `057–078` и `086–095` (с
пропусками номеров, которые никогда не создавались). Их текущая продуктовая
truth уже описана в [`docs/current-product-status.md`](current-product-status.md)
и baseline PRD. Статусы закрытых historical/cleanup/auth slices выровнены с
этой truth; оставшиеся `Draft`/planning значения обозначают requirements-only,
будущий backlog или ещё не утверждённый implementation lane. Для
runtime/release выводов используем current-product-status и feature validation
receipts; для следующего изменения сначала обновляем status этого spec, его
receipt и current-product-status одним change set.

## Текущий срез 096–120

В этом диапазоне нет каталогов `103`, `112` и `115–117` на проверяемом
`master`: это незаведённые номера, а не незаполненные feature specs. Новые
номера не стоит создавать задним числом без отдельного продуктового решения.

| Feature | Текущий статус | Открытая граница / receipt |
| --- | --- | --- |
| [096](../specs/096-product-analytics-provider-rollout/spec.md) | Интегрирована в `master`, production/runtime receipts есть; feature не принята полностью | T101 и T104 остаются открыты: T101 ждёт independent operations review, lifecycle/dashboard/approval gates; T104 ждёт финальный tracker closeout после T101. Wording checkpoint — [receipt](../specs/096-product-analytics-provider-rollout/validation/reconciliation-closeout-2026-07-21.md). |
| [097](../specs/097-workspace-account-onboarding/spec.md) | Реализована, merged, released, production receipt есть | Standalone security scan был явно пропущен по решению пользователя; это не security acceptance. |
| [098](../specs/098-calendar-auto-context-match/spec.md) | Реализована, released, production receipt есть | Manual/ambiguous/private/all-day boundaries сохранены. |
| [099](../specs/099-review-m4a-normalization/spec.md) | Реализована, merged, released, production receipt есть | Production/browser и tracker closeout зафиксированы в validation. |
| [100](../specs/100-provider-link-verified-callback/spec.md) | Реализована, merged, released, production receipt есть | Link остаётся server-verified и explicit-confirmation-only. |
| [101](../specs/101-streaming-egress-audit-semantics/spec.md) | Draft / requirements-only | Не фабрикуем plan/tasks; lifecycle vocabulary и UI/reporting остаются будущим slice. |
| [102](../specs/102-remove-legacy-audio-driver/spec.md) | Реализована и merged | Удаление legacy driver подтверждено; отдельный production release не заявляется этим feature slice. |
| [104-email](../specs/104-email-login-rls-commit/spec.md) | Реализована и deployed | RLS receipt и browser production proof находятся в [validation.md](../specs/104-email-login-rls-commit/validation.md). |
| [104-essential](../specs/104-essential-interface-polish/spec.md) | Реализована и локально валидирована | Visual target и implementation evidence есть; release/production rollout — отдельный gate. |
| [105](../specs/105-macos-app-updates/spec.md) | Реализована и released в owner-only канале | Public Developer ID, notarization и Gatekeeper proof отложены. |
| [106](../specs/106-mixed-wav-recording/spec.md) | Код реализован; acceptance/release gates открыты | T049, T063 и T064 остаются `[ ]`; installed-app, rollback и synthetic E2E proof не подменяются локальным CI. |
| [107](../specs/107-auth-return-safety/spec.md) | Реализована, merged и released | Первоначальный no-release lane был позже явно открыт; текущая release boundary зафиксирована в release notes. |
| [108](../specs/108-local-postgres-only/spec.md) | Реализована и validated | Validation-only slice; production schema/runtime не изменялся. |
| [109](../specs/109-release-signing-key-custody/spec.md) | Owner-only release evidence complete; protected two-channel path remains future scope | T022 остаётся открытым; T037 закрыт receipt `v2026.07.21.3`. Protected reviewer/cloud signer не объявляется доступным. |
| [110](../specs/110-postgres-test-acceleration/spec.md) | Реализована; validation evidence записан | Новый полный прогон после финального startup guard намеренно не повторялся. |
| [111](../specs/111-support-incident-recovery/spec.md) | Реализована, merged и released | PR #3843 и follow-up #3867 merged; release `v2026.07.18.2`; старый deploy receipt переименован в historical checkpoint. |
| [113](../specs/113-transcript-speaker-turns/spec.md) | Реализована, merged и включена в `v2026.07.21.1` | Canonical speaker-turn boundary provider-neutral; MinIO playback hotfix остаётся отдельным slice. |
| [114](../specs/114-support-incident-diagnostics/spec.md) | Реализована и merged через PR #4068 | Metadata-only support report, correlation, bounded timeline и dedupe закрыты; production deploy и installed-app receipt не заявляются. |
| [118](../specs/118-interactive-playback-timeline/spec.md) | Реализована, merged через PR #3944 и выпущена в `v2026.07.21.4` | Общая шкала playback/speaker lanes, transcript-follow и meeting-local имена спикеров; отдельный production rollout proof не заявляется. |
| [119](../specs/119-expand-meeting-app-registry/spec.md) | Реализована и merged через PR #4079 | T008 остаётся открытым: live post-deploy receipt требуется после enablement. |
| [120](../specs/120-transcript-export/spec.md) | Реализована и merged через PR #4084 | Все шесть форматов, backend и web-cabinet UI валидированы; T059 / #4083 остаётся representative-reviewer gate перед general release. |

## Реальные открытые задачи во всём архиве

Открытые задачи не закрываются этой сверкой. Их нужно показывать явно в
продуктовом статусе и закрывать отдельным evidence-backed изменением:

- `001-macos-audio-driver`: исторический legacy surface; superseded системой
  system-audio-first, не возобновлять.
- `030-mvp-experience-design-system`: T093 — stakeholder visual approval.
- `052-mvp-live-ui-proof`: T019/T020 — live installed-app/production metadata
  proof.
- `090-manual-media-upload-ui`: T072 — внешний real-recording manual-upload
  receipt.
- `096-product-analytics-provider-rollout`: T101 — operations/approval gates;
  T104 остаётся открытым до финального tracker closeout после T101.
- `106-mixed-wav-recording`: T049/T063/T064 — compatibility/rollback,
  installed-app hardware и synthetic end-to-end package proof.
- `109-release-signing-key-custody`: T022 — disposable-key workflow; owner-only
  release evidence T037 закрыт в `v2026.07.21.3`.
- `119-expand-meeting-app-registry`: T008 — live post-deploy receipt после
  enablement.
- `120-transcript-export`: T059 — representative-reviewer usability study до
  general release; synthetic QA не заменяет SC-014.

Правило для следующих feature slices: сначала определить, является ли каталог
requirements-only, implementation slice или release/production closeout; затем
синхронно обновить spec status, task state, validation receipt и
`docs/current-product-status.md`. Нельзя превращать историческую фразу «на этом
этапе ещё не реализовано» в текущий blocker после merge, но нельзя и выдавать
локальную реализацию за production acceptance.
