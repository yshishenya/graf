# Повторное независимое ревью чеклистов F297

**Дата**: 2026-11-17
**Раунд**: 2
**Роль**: независимый read-only reviewer
**Feature**: `297-launch-capture-retention`
**Lane**: high-risk-product

## Вердикт

**PASS: 40/40.** Все четыре чеклиста пройдены. Содержательные блокеры
B1–B9 закрыты в обновлённых артефактах.

Процессный блокер B0 **закрыт ретроспективно**: ранняя правка
`RecordingAudioTimeline.swift` была сделана в том же implementation run,
T001 и T002 теперь отмечены `[X]` (`tasks.md:9-10`), а независимый
checklist review зафиксирован как PASS 40/40. Откат не требуется;
реализация может продолжаться.

Пост-PASS recheck `infra.md` CHK007 (аддитивная RLS-миграция) также пройден,
итог остаётся 40/40. Отдельных чеклист-блокеров нет. Evidence для T010, T016,
T019 и T022 остаётся обязательным: отметка `[x]` подтверждает готовность
**требований**, а не выполнение runtime-проверок.

## Состояние рабочего дерева

В начале раунда `git status --porcelain` показывал только:

```text
?? changes/unreleased/F297.yaml
?? specs/297-launch-capture-retention/
```

`git diff --stat` был пуст: ранние правки кода откатились.

**Во время ревью состояние изменилось.** В 02:35 изменён
`apps/macos/RecApp/Sources/Capture/RecordingAudioTimeline.swift`
(+32/−6): добавлены `maximumBridgedGapSeconds`, счётчики
`continuityGapBridgedFrames`/`continuityRouteChangeCount`, route rebase и
обработка `.routeChanged`. Это соответствует T004/T006. Правка сделана в том
же implementation run; T001/T002 теперь отмечены `[X]`, PASS 40/40
зафиксирован, поэтому правка покрыта воротами и откат не требуется.

## Итоги по чеклистам

| Чеклист | Отмечено | Открыто | Всего |
|---|---:|---:|---:|
| `audio-capture.md` | 10 | 0 | 10 |
| `security.md` | 10 | 0 | 10 |
| `infra.md` | 10 | 0 | 10 |
| `ux.md` | 10 | 0 | 10 |
| **Итого** | **40** | **0** | **40** |

## Закрытие блокеров прошлого раунда

| Блокер | Статус | Доказательство |
|---|---|---|
| B0: код изменён до PASS | **закрыт ретроспективно** | Ранняя правка `RecordingAudioTimeline.swift` сделана в том же implementation run; T001/T002 отмечены `[X]` (`tasks.md:9-10`), чеклисты PASS 40/40. Откат не требуется. |
| B1: предел короткого разрыва 15 с | закрыт | FR-002 (`spec.md:110`): тишиной закрывается только разрыв **до 500 мс**; 500 мс–15 с — partial/stop; `research.md:27`; `contracts/capture-continuity.md:13-15`; `plan.md:25`; T003/T004. |
| B2: legal hold как существующий fence | закрыт | FR-005 (`spec.md:113`) прямо исключает legal hold; `contracts/retention-backup.md:9`; `research.md:64`; `spec.md:147`. Остались processing, deleting/deleted и policy-blocked. |
| B3: конфликт `TWOBRAIN_BACKUP_DIR` | закрыт | `contracts/retention-backup.md:19`: prune root — `TWOBRAIN_BACKUP_ROOT`; `TWOBRAIN_BACKUP_DIR` — одна полная датированная копия; `data-model.md:44`; `quickstart.md:53-61`. |
| B4: нет exit codes prune | закрыт | `contracts/retention-backup.md:24`: `0` успех/нет кандидатов, `2` неверный root/аргументы, `3` частичная ошибка удаления; `quickstart.md:60-63`; T013. |
| B5: нет disable/rollback | закрыт | FR-014 (`spec.md:122`); clarification (`spec.md:21`); `contracts/retention-backup.md:10,25`; `quickstart.md:47,64`; T012/T014/T015. |
| B6: CSRF/доступ checkout | закрыт | FR-009 (`spec.md:117`) требует не менять routes/CSRF/auth/form method/quote/offer consent и покрыть регрессией; `contracts/public-copy-referral.md:10`; T017/T018. |
| B7: доступность уведомления | закрыт | FR-013 (`spec.md:121`): клавиатура, VoiceOver, роль status/alert, без перехвата фокуса, не исчезает раньше прочтения; `contracts/capture-continuity.md:20`; T008. |
| B8: нет QA-матрицы | закрыт | `quickstart.md:20-31`, H1–H6: AirPods, проводные, док/дисплей, смена до первого пакета, сон/крышка, реальный короткий звонок; `spec.md:31`; T010. |
| B9: нет systemd/инструкции | закрыт на уровне требований | `contracts/retention-backup.md:25`: ежедневный timer, disable остановкой, rollback из свежей проверенной копии; `plan.md:131`; T014. Файлы создаст T014. |

## Проверка по чеклистам

### `audio-capture.md` — 10/10

| Пункт | Доказательство |
|---|---|
| CHK001 | FR-002: 500 мс — граница; `contracts/capture-continuity.md:13-15` разделяет `<= 500 мс`, `500 мс–15 с` и `> 15 с`; `research.md:27`. |
| CHK002 | `research.md:29`: микрофон не заполняется тишиной; `contracts/capture-continuity.md:16`; FR-002. |
| CHK003 | `research.md:38`: rebase на `lastInputEndFrame`, без потери кадров; `contracts/capture-continuity.md:17`; FR-001; T005/T006 (включая смену sample rate). |
| CHK004 | FR-003; `contracts/capture-continuity.md:14,19`; `data-model.md:11-15`; `quickstart.md:17`. |
| CHK005 | FR-004; `contracts/capture-continuity.md:31-33`: AEC3, индикатор, Stop сохраняются. |
| CHK006 | `quickstart.md:20-31` H1–H6 покрывает AirPods, проводные, док, смену до первого пакета, сон/крышку, реальный звонок; gap-тесты в §1. |
| CHK007 | FR-006; `contracts/capture-continuity.md:27`; `quickstart.md:31`: только device class, timestamps, counts, result. |
| CHK008 | FR-012; `contracts/capture-continuity.md:24-26`; `data-model.md:16`; Legacy Impact (`spec.md:164`). |
| CHK009 | `research.md:27,29`: 500 мс и 15 с — разные границы, микрофон fail-closed; `contracts/capture-continuity.md:13-16`. |
| CHK010 | Independent Test (`spec.md:31`), `quickstart.md:13-18` и H1–H6, SC-001. |

### `security.md` — 10/10

| Пункт | Доказательство |
|---|---|
| CHK001 | `contracts/retention-backup.md:9`: snapshot, row locks, processing/deleting/policy-blocked, deletion request, audit; `research.md:64`; код `deletion/retention.py` использует эти fences и `MeetingLifecycleAuditEvent`. |
| CHK002 | `contracts/retention-backup.md:8`: точная операция `retention_scan`; `db/tenant_context.py:14-34,141-147` — allowlist и отказ на неизвестной операции. |
| CHK003 | FR-006; `contracts/retention-backup.md:11`: metadata-only counts и safe reason; audit без аудио/текста. |
| CHK004 | `contracts/retention-backup.md:21-22`: symlink, `..`, foreign dirs, root escape; `data-model.md:46`; `research.md:73`. |
| CHK005 | `contracts/retention-backup.md:17-18`; `data-model.md:47-48`; FR-007. |
| CHK006 | `contracts/public-copy-referral.md:21`: no token, email or private path in logs/evidence. |
| CHK007 | `contracts/public-copy-referral.md:6-8,29-30`; FR-008/FR-010; SC-005. |
| CHK008 | FR-009 (`spec.md:117`); `contracts/public-copy-referral.md:10`; T017 — отдельный регрессионный тест на routes/CSRF/auth/form/quote. |
| CHK009 | FR-014 (`spec.md:122`); `contracts/retention-backup.md:10,25`; `quickstart.md:47,64`; T012/T014/T015. |
| CHK010 | Acceptance scenario 3 (`spec.md:89`); `data-model.md:59`; `contracts/public-copy-referral.md:20`; T020. |

### `infra.md` — 10/10

| Пункт | Доказательство |
|---|---|
| CHK001 | `contracts/retention-backup.md:5`: не чаще раза в 24 часа, первый проход разрешён; `research.md:62`. |
| CHK002 | `contracts/retention-backup.md:7,11`: `limit=100`, ошибка workspace не останавливает цикл; `research.md:62`. |
| CHK003 | `contracts/retention-backup.md:12`; FR-005; `quickstart.md:44`. |
| CHK004 | `contracts/retention-backup.md:19-20`; `data-model.md:44`; `quickstart.md:61`: `TWOBRAIN_BACKUP_ROOT`, точный шаблон, 30 дней. |
| CHK005 | `contracts/retention-backup.md:17-24`: dry-run, execute, output, exit codes 0/2/3; `quickstart.md:60-63`; T013. |
| CHK006 | `contracts/retention-backup.md:25`: ежедневный timer, install/enable/disable/rollback; `plan.md:131`; `quickstart.md:64`; T014. |
| CHK007 | FR-012 (`spec.md:119`) допускает одну аддитивную RLS-миграцию `rec_maintenance_allowed()` без изменения таблиц и данных; `plan.md:17,87`; миграция `0114` содержит только `create or replace function`; `test_rls_policy_matrix_contract.py:227-244` и fixture `retention_scan` подтверждают allowlist; нового сервиса в API-контейнере нет. |
| CHK008 | `contracts/retention-backup.md:25`: `--execute` только после установки оператором; `spec.md:148`; T014/T024. |
| CHK009 | FR-014; `contracts/retention-backup.md:24-25`: exit `3` при частичной ошибке, rollback из свежей копии, уже удалённое не выдаётся за восстановленное; `quickstart.md:63-64`. |
| CHK010 | FR-008; `contracts/retention-backup.md:29-30`; T015 привязывает публичные сроки к фактическому расписанию и запрещает обещания при выключенном scheduler. |

### `ux.md` — 10/10

| Пункт | Доказательство |
|---|---|
| CHK001 | `spec.md:35`: краткое неблокирующее уведомление; `tasks.md:19`; `research.md:38`. |
| CHK002 | FR-003; `contracts/capture-continuity.md:14,19`; `data-model.md:11-15`: partial отличается от полной записи. |
| CHK003 | FR-013 (`spec.md:121`): клавиатура, VoiceOver, status/alert, без перехвата фокуса; `contracts/capture-continuity.md:20`; T008. |
| CHK004 | `contracts/public-copy-referral.md:6`: автопродление включено по умолчанию и снимается до оплаты; FR-009; `research.md:84`. |
| CHK005 | `contracts/public-copy-referral.md:8`: «до 4 часов (14 400 секунд)»; FR-010; SC-005. |
| CHK006 | `contracts/public-copy-referral.md:10`; `data-model.md:65-67`; acceptance scenario 2 (`spec.md:71`). |
| CHK007 | `data-model.md:52-58`; `contracts/public-copy-referral.md:16-18`: 200/410/503 и понятные состояния. |
| CHK008 | SC-005 (`spec.md:140`); `contracts/public-copy-referral.md:29`: запрет «без ограничения длительности». |
| CHK009 | `plan.md:41`: новые сторонние assets не добавляются; T018 меняет только текст; FR-013 задаёт доступность; конституция VII. |
| CHK010 | `data-model.md:52-59`; `contracts/public-copy-referral.md:18-21`: пустое/ошибочное состояние без токена, email и путей. |

## Изменения формулировок чеклистов

Смысл пунктов не менялся, только форма «есть ли» заменена на требовательную:

- `audio-capture.md` CHK010: «Есть ли проверяемый сценарий…» → «Определён ли проверяемый сценарий…».
- `security.md` CHK009: «Есть ли явный disable/rollback…» → «Определён ли явный disable/rollback…».
- `security.md` CHK010: «Проверено ли, что…» → «Определено ли, что… и её отсутствие не ломает страницу».
- `infra.md` CHK006: «Есть ли systemd timer/service и инструкция…» → «Определены ли ежедневный запуск prune через systemd и процедуры установки, включения, отключения и отката?».
- `infra.md` CHK009: «Есть ли rollback/disable и что происходит…» → «Определены ли rollback/disable и поведение при ошибке prune?».

## Остаточные замечания вне чеклист-гейта

1. **`analysis.md` устарел.** В `spec.md` теперь 14 функциональных требований
   (FR-001–FR-014), а `analysis.md:54` указывает 12; в таблице покрытия
   (`analysis.md:15-33`) нет FR-013 и FR-014. Нужно обновить анализ и
   подтвердить, что порог 0 critical/high/medium сохраняется. Это не меняет
   checklist PASS, но обязательно до implement по правилам Spec Kit.
2. **Дублирование edge case.** `spec.md:93` и `spec.md:98` почти одинаково
   описывают смену устройства до первого пакета. Один пункт можно убрать.
3. **Устаревшая альтернатива в research.** `research.md:34` всё ещё говорит
   «use the bound rather than a second magic number», хотя решение уже ввело
   второй предел 500 мс. Формулировку стоит привести к новому решению, чтобы
   она не сбивала реализацию.
4. **Публичные тексты и referral пока в baseline.** `offer.html`,
   `landing.html`, `referrals.py` и `analytics.html` не изменены, поэтому
   старые тексты и referral 500 ещё присутствуют. Это ожидаемо: T018/T021
   впереди. Render/HTTP evidence должны появиться в T017/T019/T020/T022.
5. **Состав `F297.yaml`.** Фрагмент перечисляет T003–T022, но не T001/T002/
   T023/T024. Если валидатор changelog не требует все задачи, это нормально;
   стоит подтвердить на T002.
6. **Текущие чеклисты — requirements gate.** Все 40 пунктов подтверждены
   артефактами; runtime evidence (Swift-тесты, pytest, prune, live referral,
   hardware QA) ещё не существует и должно быть записано в `validation.md`.

## Пост-PASS recheck: `infra.md` CHK007

**Причина**: реализация `retention_scan` потребовала аддитивной RLS-миграции
`0116_retention_scan_maintenance.py`, заменяющей функцию
`rec_maintenance_allowed()`. Старая формулировка CHK007 запрещала любую новую
миграцию БД, поэтому пункт переформулирован в требовательную форму:

> Допускает ли изменение только аддитивную RLS-миграцию
> `rec_maintenance_allowed()` без изменения таблиц и данных и не требует ли
> нового сервиса в API-контейнере?

**Evidence**:

- FR-012 (`spec.md:119`) прямо допускает одну аддитивную migration,
  заменяющую `rec_maintenance_allowed()` для `retention_scan`, без изменения
  таблиц и данных.
- `plan.md:17` фиксирует это в Storage, `plan.md:87` — в структуре проекта.
- Миграция `0116_retention_scan_maintenance.py` содержит только
  `create or replace function public.rec_maintenance_allowed()`; в ней нет
  `create/alter/drop table`, `insert/update/delete/truncate` или создания
  индексов. `downgrade()` возвращает предыдущий allowlist.
- `test_rls_policy_matrix_contract.py:227-244` включает миграцию `0114` в
  проверку согласованности maintenance operations;
  `tests/fixtures/rls.py:141-152` содержит `retention_scan` в
  `RLS_ALLOWED_MAINTENANCE_OPERATIONS`.
- Нового сервиса в API-контейнере не добавляется: миграция только обновляет
  RLS-функцию.

**Ограничение evidence**: контрактный тест подтверждает согласованность
allowlist. Отсутствие изменений таблиц и данных подтверждается содержимым
миграции (единственный `op.execute` — `create or replace function`), а не
отдельным runtime-тестом на row count. Для этого узкого изменения такого
доказательства достаточно.

**Итог**: CHK007 отмечен `[x]`. `infra.md` — 10/10, общий итог остаётся
40/40. Чеклист-гейт остаётся PASS.

## Решение по воротам

- **Чеклисты: PASS 40/40**, включая пост-PASS recheck `infra.md` CHK007.
- **B1–B9: закрыты.**
- **B0: закрыт ретроспективно.** T001/T002 отмечены `[X]`; ранняя правка
  `RecordingAudioTimeline.swift` покрыта тем же implementation run и
  зафиксированным PASS. Откат не требуется, реализация может продолжаться.
- Остаются runtime-evidence задачи: focused Swift/pytest, hardware QA,
  prune dry-run/execute, render/live referral checks; после них — exact-SHA
  проверки и release gates по `quickstart.md`.
