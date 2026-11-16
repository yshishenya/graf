# T104 Checklist: применимость требований к server union cbdbae7

**Purpose**: Независимая проверка полноты, ясности и согласованности существующих требований F200/T104 при сведении с F140 `cbdbae725e14a7c261210ca0e56f7fd9087b5b48`; без новых продуктовых требований.
**Created**: 2026-11-12.
**Feature**: [F200 spec](/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup/specs/200-windows-desktop-app/spec.md), [T104](/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup/specs/200-windows-desktop-app/tasks.md:472).
**Analysis**: [Ограниченный анализ применимости и карта источников](/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup/.dev/f200-master-sync/cbdbae725e14/t104-requirements-applicability-2026-11-12.md).

**Note**: Создан по `speckit-checklist`; это проверка качества и применимости требований, не приёмка кода или список результатов тестов.
**Review Ownership**: Независимый reviewer (передача Rawls через main после его текущего отчёта). Автор/исполнитель реализации отметки не меняет.
**Marker Semantics**: `[x]` означает подтверждённое reviewer качество требований по конкретному evidence. Не означает выполненную реализацию, тесты, выпуск или закрытие T104. Исходно **0 checked / 10 unchecked**.

## Полнота области и зависимостей

- [x] CHK001 Достаточно ли явно связаны существующие требования с T104 B2c.1/2/11/13/14b и разрешёнными 29+9 путями, чтобы сведение не расширяло продукт, владение Pascal/Rawls/main или область до следующего F292 delta? [Полнота, Spec §Session 2026-11-08 T104 и §T104/B2c.14b; Plan §T104/B2c; Tasks T104; Analysis §Точная идентичность и границы]
- [x] CHK002 Однозначно ли применены действующие требования сохранения истории к 127 published master migrations и линейному графу `0113_fair_use_operator_history → 0114_f200_calendar_upload_pin → 0115_f200_strict_upload_journal`, с сохранением тел F200 и собственных metadata/imports F140? [Ясность, Spec FR-012/013/022, SC-005/008; Plan §T104/B2c.14 «Порядок реализации и откат»; Analysis §Что именно reviewer должен оценить]
- [x] CHK003 Явно ли отделены достаточность разрешённого локального переноса IDs и ограничения provenance: известные временные применения, неизвестные долговечные БД/внештатные публикации и отдельный план совместимости при их обнаружении? [Предпосылки, Analysis §История и происхождение; migration-id-provenance-2026-11-12.md; Spec FR-012/013, SC-008]

## Ясность отказов и согласованность механизмов

- [x] CHK004 Достаточно ли точно задано применение раннего отказа шести полным прежним IDs, unknown/multi/read-error и положительного published master ID до изменений выпуска, без stamp/ручной подмены версии или запрета по числовому префиксу? [Ясность, Analysis §Что именно reviewer должен оценить; Spec §T104/B2c.14b; Release execution plan §Следующий срез T104]
- [x] CHK005 Согласованы ли требования минимальных прав и атомарности F200 bootstrap с F140 immutable-history writer/ACL/RLS/functions/triggers/index, включая отказ без окна расширенных grants и настоящее runtime LOGIN evidence? [Согласованность, Spec FR-014/022; Plan §T104/B2c.14; F140 Contract §Защита истории на уровне PostgreSQL и §Выбранный SQL-механизм в target SHA; Analysis §Совмещение]
- [x] CHK006 Полно и непротиворечиво ли применены protected-history preflight/0-effects/rollback F140 к F200 interrupted-object cleanup, включая владение session/revision/tenant и ограниченный retry до commit? [Покрытие ошибок, Spec FR-022; Data model §T104/B2c.13–B2c.14b; F140 Contract §Защита истории на уровне PostgreSQL; Analysis §Совмещение]
- [x] CHK007 Сохраняет ли интерпретация требований обе F200 account-closure/deletion-purge sessionmaker границы вместе с F140 notification authorization/suppression/retry, без нового bypass и без объявления всей F140 принятой? [Согласованность, Spec FR-014/022; Plan §T104/B2c.14; F140 Contract §Письмо и исходный адресат и §Существующие эффекты и граница; Analysis §Совмещение]

## Измеримость и пределы доказательств

- [x] CHK008 Достаточна ли связь существующей матрицы migration/integration/rollback с рисками union, полной схемой и реальными runtime LOGIN фикстурами, чтобы положительный сценарий не доказывался owner/SET ROLE/production bypass или одним Alembic marker? [Измеримость, Quickstart §T104/B2c.13–14 и §Управляемый запуск исправления T104; F140 Contract §Выбранный SQL-механизм; Analysis §Проверки после независимого gate]
- [x] CHK009 Однозначно ли различены качество требований, будущие focused checks, server exact-tree/CI, неизменность Windows/R2 от этого bounded delta и отдельные installed/hardware/release gates, без переноса старого source_tree на новый продукт? [Ясность, Spec SC-005/006/008; Release execution plan; Analysis §Проверки после независимого gate; Constitution VI]
- [x] CHK010 Полно ли определены условия применения review: target SHA отдельно от PR base/origin master, SHA-256 dirty-пересечений, независимые отметки/evidence, собственное чтение перед кодом, изоляция стенда/df/Docker параметры и остановка при новом пути вне разрешённого набора? [Зависимости, Constitution VI; spec-kit-flow.md §§4/6/8; document-reading.md; Analysis §Точная идентичность и границы и §Передача независимому reviewer]

## Notes

- Все ссылки на F140 contract относятся к исходным Git-байтам `cbdbae725e14a7c261210ca0e56f7fd9087b5b48`, а не к отсутствующему пока рабочему файлу; полный путь `specs/140-user-account-billing/contracts/fair-use-operator.md`.
- Карта Analysis содержит абсолютные ссылки на оригиналы и manifest; старые требования migration/integration/rollback сохраняют силу без переписывания здесь.
- Reviewer проверяет каждый пункт, записывает конкретные источники/хеши и объясняет каждый неподтверждённый пункт; итоговые checked/unchecked пересчитывает после своих изменений. Старые 680 критериев не выдаются за повторно проверенные.
- `speckit-implement` только читает отметки. До независимого полного PASS нового checklist и остальных ворот код этого среза остаётся на стопе. Нового решения владельца или повторного T124 checklist не требуется.
- Выполнение тестов, выпуск, VM/prod и закрытие issue этим checklist не разрешаются автоматически; действующие полномочия и gates сохраняются.
- Независимое ревью Rawls/Codex завершено 2026-11-12: **10 checked / 0 unchecked**, findings требований **C0/H0/M0/L0**. [Собственный отчёт и квитанция чтения](/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup/.dev/f200-master-sync/cbdbae725e14/independent-t104-gate-review-2026-11-12.md) содержит evidence отдельно по CHK001–CHK010. Все 38 manifest hashes/ожидаемых отсутствий MATCH; исходное состояние published migrations: 126 byte-identical + 1 absent incoming, 0 different. Требование будущего кандидата — 127/127.
- PASS относится к качеству и применимости существующих требований для bounded T104/#7281 union target `cbdbae725e14a7c261210ca0e56f7fd9087b5b48`. Допускает дальнейшую реализацию только вместе с прочими воротами и собственным обязательным implementation чтением Sartre. Это не code review, не результат migration/runtime tests, не включение strict writer, не приёмка Windows/notices/выпуска. Прежние 680 пунктов повторно независимо не оценивались.
