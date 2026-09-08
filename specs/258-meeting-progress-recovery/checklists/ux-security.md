# UX и безопасность: качество требований F258

**Purpose**: требования готовы к high-risk реализации.
**Created**: 2026-09-08
**Feature**: [spec.md](../spec.md)
**Review Ownership**: независимый reviewer; [x] означает принятие качества требований, не готовность кода. Implement не меняет маркеры.

## Полнота и непротиворечивость

- [x] CHK001 Определена ли независимость звука/расшифровки/итогов, включая пустой slot и закреплённый исходник? [Spec FR-001–003]
- [x] CHK002 Различены ли долгий pending, временная недоступность, окончательная ошибка и частичный результат? [Spec FR-003–004; contracts/progress.md]
- [x] CHK003 Заданы ли автоматическое обновление, offline/сон/возврат и сохранение player/focus/draft? [Spec FR-004–005; SC-001]
- [x] CHK004 Явно ли указан ограниченный пересмотр F249 FR-020 при сохранении F255 menu и capture guards? [Spec FR-006–007]
- [x] CHK005 Разделены ли подтверждение старта/Stop, готовность результата и фактическая OS delivery? [Spec US2; SC-004]
- [x] CHK006 Достаточно ли определены простые подписи, действие, 200%, темы, клавиатура и постоянный Stop? [Spec FR-011; SC-005]

## Приватность и восстановление

- [x] CHK007 Определены ли owner/scope/epoch, unknown-session и удаление/отзыв доступа без утечки? [Spec FR-009; data-model.md]
- [x] CHK008 Описаны ли сохранение прежних false, явное включение recap, разрешение ОС, Focus и звук при capture? [Spec FR-008; contracts/progress.md]
- [x] CHK009 Различены ли retry, новое возникновение после recovery, старые события и notification freshness/retention? [Spec FR-010; data-model.md]
- [x] CHK010 Ограничены ли DB lookup права и сохранены ли RLS/deletion/source fences? [Spec FR-012]
- [x] CHK011 Отделены ли наблюдения Krisp от предположений, исключены ли извлечённые код/ресурсы/частное содержимое? [research.md; Spec Assumptions]
- [x] CHK012 Явны ли тестовые границы, отсутствие production/release и порядок commit/Dev/PR? [plan.md; quickstart.md]

## Notes

Генерация оставляет все пункты открытыми. Результат review записывается reviewer здесь.

### Независимая проверка требований — 2026-09-08

Приняты CHK001–CHK012: 12/12. CRITICAL/HIGH пробелов требований в пределах
этого checklist не обнаружено. Прочитаны spec, plan, research, data-model,
contracts/progress, quickstart, tasks и оба checklist F258, конституция 7.0.0;
учтён предыдущий независимый разбор F249. Код сопоставлен с исходным SHA
`e81b412dff920cc29ed37de60be13dd8fc4d1c43`. Это принятие требований, не
подтверждение реализации, доставки macOS или прохождения analyze.

- CHK001–002: FR-001–003, модель двух независимых осей «опубликованный результат /
  новая попытка» и матрица progress различают пустой slot, ожидание, partial и
  terminal. Research запрещает подмену исходника невалидного опубликованного
  результата; T002–T003 покрывают фактический `_latest_accepted_media_revision`
  (`cabinet/egress.py:1187`) и проекцию `processing/status.py:291`.
- CHK003, CHK006: FR-004–005/011, SC-001/005 и quickstart задают 15 секунд для
  активного экрана, возврат после сети/сна, сохранение player/focus/draft,
  выбранного формата, темы и 200%. T004–T005 адресуют реальные остановки опроса
  и reload (`cabinet.js:3202,3559`); GET не разрешает новую генерацию.
- CHK004–005: FR-006–007 явно ограничивают пересмотр F249 FR-020 готовностью
  собственной записи; F255 menu и защищённый countdown сохраняются. Контракт
  отделяет подтверждённый capture/Stop от готовности и фактического баннера;
  T006–T008 относятся к существующим переходам `TwoBrainRecApp.swift:1939,2301`
  и presenter, а не к новому контроллеру записи.
- CHK007–008: FR-008–009, plan и data-model запрещают перепривязку unknown
  sessions, требуют проверенного scoped context и отмены старой epoch.
  Нейтральный payload, повторная проверка клика, явное включение recap
  (старое отсутствующее значение false), сохранение прежних false и уважение
  OS/Focus прямо заданы. Это адресует ownership/foreground ограничения F249
  (`DesktopNotificationPresenter.swift:33,191,340,357`).
- CHK009: FR-010 и data-model отделяют occurrence после подтверждённого recovery
  от retry, свежесть от retention и текущий переход от старого ready при запуске.
  T009–T010 и quickstart требуют две записи/чужой primary/>5 групп/expiry;
  соответствующие причины находятся в `DesktopNotificationPresenter.swift:89`
  и `DesktopUploadCustodyProjection.swift:666`.
- CHK010: FR-012, research §7, T009–T010 и quickstart требуют только нужный
  metadata SELECT, проверку настоящей media role, отказ DML и чужой scope,
  сохранение RLS/deletion/source. Это соответствует lookup в
  `normalization/worker.py:237` и отсутствию processing_workflows среди текущих
  media grants (`bootstrap_runtime_database_roles.py:16`).
- CHK011–012: research отделяет наблюдения Krisp от неизмеренной доставки,
  запрещает извлечённые ресурсы/частное содержимое; spec/plan/quickstart
  сохраняют собственный код, synthetic evidence, единственный GRAF Dev,
  exact-SHA проверки и явный порядок commit → Dev → PR. Merge/release/production
  исключены; непроверенные аппаратные сценарии остаются открытыми.

Рецензент изменил только этот checklist. Проверки реализации, UI, production,
коммиты и внешние действия в этой проверке не выполнялись. Порядок внедрения
по-прежнему требует analyze и сопоставления GitHub-задач главным агентом.
