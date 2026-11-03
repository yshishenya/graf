# Повторная приёмка F262/T012: состояние записи и текущий доступ

Дата: 2026-10-22. Issue: #6887; итоговая задача #6896 остаётся открытой.
Ветка: `codex/262-lifecycle-lookup-audit`.
Текущая основа PR: `71a3d75d3bc25fd29b302df59064a090feac210d`.
Исходная основа первой локальной проверки:
`3758e61d723160d57a1702b58afd5e5c2bbed8c0`.
Точный PR SHA и обязательные GitHub checks фиксируются в описании PR и
итоговом комментарии issue после слияния.

## Область и исходный результат

Lane: active-spec-kit, существующая high-risk-feature F262/T012.
Проверены исходные критерии issue, spec, plan, tasks, quickstart,
contracts/lifecycle, data-model, research и применимые требования доступа
и удаления. Дефект рабочего сервера в этой области не обнаружен.
Сохраняются содержательные новые проверки в существующем integration-модуле;
код продукта, схема и зависимости не меняются.
Исторический PR #6911 не используется как текущее доказательство CI:
его обязательный артефакт больше недоступен. PR #7726 принимал T010/T011,
поэтому приёмка T012 проводится отдельным связанным изменением.

## Analyze до переноса

Сопоставление 22 FR / 7 SC с 23 задачами из analysis.md перепроверено для
активного T012; новый контракт не вводится. Применимые FR-002/004/007–009/019/022
покрываются T012 и его зависимостями T008–T011/T013/T019/T021.
Для T012: CRITICAL 0, HIGH 0, неразрешённых уточнений 0; задача уже имеет
владельца #6887, дубликаты не создаются. Общая F262 и её установленные,
временные и выпускные критерии этим анализом не объявлены выполненными.
Независимый reviewer до переноса перечитал оба чеклиста: 20 checked,
0 unchecked; основания каждого пункта —
[review-t012-lookup-checklists-20261022.md](review-t012-lookup-checklists-20261022.md).

## Постоянные проверки

В `test_recording_origin_cancellation.py` добавлены три случая:

- Настоящий AuthSession с trusted привязкой устройства сохраняется через
  выдачу и отзыв share grant. Чужой origin остаётся unavailable; разрешённый
  meeting даёт allowed. После отзыва тот же сеанс больше не получает доступ.
  Удалённую встречу обычный читатель не видит, а изменение текущей роли в БД
  на admin разрешает accepted receipt исходного запроса без чужого origin.
- Meeting и cancellation другого workspace не раскрываются по обоим типам
  поиска: unavailable без receipt и meeting_id. Изменение workspace касается
  только синтетических строк изолированной тестовой БД, не пользовательских данных.
- Отзыв membership после успешного lookup тем же сеансом возвращает 403
  workspace_scope_denied без receipt.

Существующий bounded case усилен: 100 суммарных целей с повторами дают две
уникальные записи; 101 цель суммарно, пустой запрос, extra field, неверный UUID,
пустой и слишком длинный origin дают 422. Граница проверяется до deduplication.
Сохраняются no-store, отсутствие title/transcript и разделение own-origin /
meeting manager. Отсутствие доступа не выдаётся за подтверждённое удаление.

## Исполнение окончательных тестов

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused -q \
  tests/integration/test_recording_origin_cancellation.py \
  tests/integration/test_recording_sync_processing.py::test_unavailable_deletion_target_has_no_receipt_and_next_target_can_be_deleted \
  tests/integration/test_recording_deletion_scope_acceptance.py::test_origin_only_receipt_creates_no_meeting_or_meeting_purge_foreign_keys
```

Результат: **23 разных теста PASS, 0 FAIL / 0 SKIP**, 2 прежних предупреждения,
18.85 s pytest; focused phase 23 s. Штатный runner удалил изолированный контейнер.
Collection digest: `f2a1d1b3bc1261d743477f58f9e8b4ae61d08a338ffd4e5e7caf4b059e11479a`.
В эти 23 входят новые три случая. Предыдущие запуски, внешние 3/6 cases
и исторические 11 schema cases повторно не прибавляются.

Журнал: `f262-t012-final-permanent-tests-20261022.log` в локальном
реестре issues-334-audit. Только результаты и хеши, без содержимого встреч.

- SHA-256 тестового файла: `b798aea82c9512683a856c8864eff0e832020bb6b35568591dc5ba4d6db91252`.
- SHA-256 окончательного журнала: `4fbcb1aaec900923b3d7165d5124cfd49cfaefd331fb03ae628e135acfae3273`.

Ruff, git diff --check, check_spec_kit_governance.py,
check-development-process.py, validate-legacy-impact.py и проверка
собственного changelog fragment — PASS.

## Converge и пределы

### Повтор после переноса на текущую основу

На чистом `a5efee374cfa2676b736e81af53f84dbb8f1ee16` (родитель и
merge base `71a3d75d3bc25fd29b302df59064a090feac210d`) та же команда
повторена полностью: **23 passed, 0 failed / 0 skipped**, 2 прежних
предупреждения, 19.69 s pytest, focused phase 23 s; контейнер удалён.
Collection count/digest совпали с исходным прогоном. Журнал:
`f262-t012-rebased-permanent-tests-20261022.log` в `issues-334-audit/`,
SHA-256 `9bcf84a8089973d4e913ee9e4190ff5052fff7be142cc2e8895230c495bff30a`.

Изменение основы состоит из восьми файлов F281: публичного шаблона
инструкции Zoom, собственного changelog, плана продвижения и документов
F281. Auth/API/lookup и окончательный integration-модуль F262 совпадают
с первоначально проверенными байтами; хеш теста b798aea8…db91252 сохранён.
Последующая редакционная правка исправляет указание текущей основы и
заменяет локальный путь в reviewer-отчёте абстрактным идентификатором
реестра. Выводы независимого ревью не меняются; новая редакция получает
собственные точные GitHub checks. Повторные 23 не прибавляются к исходным.

Применимый T012 сопоставлен с selector, schema, API/auth dependencies и
lifecycle manager resolver: незакрытого обязательного пробела в этом срезе
не найдено. Сохраняется историческая отметка T012 в tasks.md; новых задач
и пустой секции convergence не добавлено. Независимое ревью окончательной
дельты фиксируется отдельно в review-t012-lookup-tests-20261022.md.

Это приёмка серверного lookup; она не заменяет нативный цикл T013,
всю S01–S51, измерение UI/SC-003, аппаратную приёмку, выпуск или production.
GRAF Dev и пользовательские данные не менялись. Закрытие #6887 допустимо
только после трёх обязательных GitHub checks точного SHA/основы, слияния,
подробного комментария и успешного live closeout.
