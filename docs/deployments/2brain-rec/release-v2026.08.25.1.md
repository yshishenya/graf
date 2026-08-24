# Production closeout: `v2026.08.25.1`

## Immutable release

- Tag and GitHub Release: [`v2026.08.25.1`](https://github.com/yshishenya/graf/releases/tag/v2026.08.25.1)
- Release and production SHA: `5192e7455e1e65f2bc9bd3273756c7149cc83c1e`
- Implementation PR: [#5801](https://github.com/yshishenya/graf/pull/5801)
- Дата выкладки и closeout: 2026-08-25

Receipt содержит только агрегированные технические метаданные. Секреты,
учётные данные, signed URLs, аудио, расшифровки и содержимое встреч не
включались.

## Что исправлено

Статус обработки теперь применяется только к строке с тем же `meeting_id` и
к актуальному поколению DOM-списка. Устаревшие запросы отменяются, ответы после
обновления списка игнорируются, а API запрещает кэширование статуса и проверяет
идентичность записи в ответе.

## Validation evidence

| Гейт | Результат |
| --- | --- |
| Contract/accessibility tests | PASS; 66 тестов |
| Processing API, tenant authorization и cabinet meeting-list | PASS; 37 тестов с disposable PostgreSQL |
| Node syntax, Ruff, `git diff --check` | PASS |
| Backup и restore rehearsal | PASS |
| Migration, runtime identity, Temporal и processing worker readiness | PASS |
| Production smoke | PASS |
| `/api/v1/health/live` и `/api/v1/health/ready` | PASS; HTTP 200 |
| Production `cabinet.js` | PASS; asset совпал с локальным SHA |
| Full local CI | Не запускался по явному указанию владельца релиза; это не считается full-CI pass |

Deploy выполнен через `--skip-local-ci`. Остальные remote deployment gates,
включая backup/restore, readiness, health и smoke, прошли.

## Воспроизведение и ручная проверка

Исходный баг вручную не воспроизведён: точная последовательность действий и
частота появления неверного статуса неизвестны. Это ограничение зафиксировано,
а защита от регрессии покрыта контрактными и интеграционными тестами.

Для ручной проверки в авторизованной сессии нужен список минимум из двух
записей, одна из которых находится в обработке:

1. открыть список встреч;
2. запустить или дождаться обработки записи `456`;
3. оставить список открытым на несколько циклов обновления статуса;
4. обновить список или изменить фильтр во время обработки;
5. убедиться, что статус отображается только в строке `456`, а не в соседней
   записи.

Authenticated browser smoke конкретных записей в production не выполнялся:
доступная browser-сессия была без авторизации. Поэтому этот сценарий остаётся
ручной follow-up проверкой, а не заявленным production evidence.

## Known limitations и post-deploy follow-ups

- Полный CI сознательно пропущен; release считается выпущенным с этим явно
  принятым исключением.
- Runtime сообщил штатные post-deploy follow-ups: automatic retry, backfill
  inventory, range playback и normalization cleanup.
- Изменений схемы данных, processing workflow, provider API и миграций для этой
  правки нет.

