# Проверки F286

Полоса: high-risk-feature. Данные синтетические, PostgreSQL одноразовый; настоящие письма не отправлялись.

## Реализация и локальные проверки

- Новые AUTO/sharing/delivery/deletion плюс UI contract: 52 passed, 34.19s. Команда: `bash apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_summary_autosend.py tests/integration/test_summary_sharing.py tests/integration/test_summary_delivery.py tests/integration/test_summary_deletion.py tests/contract/test_recording_share_ui_contract.py -q`.
- Существующие invitation/UI/public links, projection, maintenance: 36 passed, 27.36s.
- Старые meeting shares/shared-with-me/invitation workflow, deletion races и новые deletion/UI: 44 passed, 54.61s.
- UI/error, deletion secrecy, calendar normalization, Dev maintenance contract, share-link contract, analytics consent: 45 passed, 5.25s.
- Node `summary-sharing-state.test.cjs`: PASS; JS syntax, shell syntax installer, Ruff src/new tests, diff whitespace и Spec Kit governance: PASS.
- Runtime PostgreSQL: session_user `twobrain_rec_app` reservation и `twobrain_rec_maintenance` scan→snapshot→batch→reservation проверены, без superuser/BYPASSRLS. Без maintenance context данные не видны. Миграции 0102–0103 применены изолированным runner.
- Неизвестная доставка не повторяется; terminal Temporal восстанавливает только неначатые адресаты; deadline завершает pending для created/started dispatch; replay старого invitation не перепривязывает документ к новому разрешению. Отзыв и deletion проверены интеграционно.
- Network вызов Postal вынесен за фиксирование reservation; real inbox acceptance не утверждается.

## Сходимость

Выполнен `$speckit-converge`: актуальные spec/plan/tasks и конституция сверены с моделями, миграциями, API, reader, workflow/recovery, AUTO guards, cleanup и UI. FR-001–024, SC-001–005 и четыре истории имеют реализацию/проверки. Дополнительных незапланированных частей реализации не обнаружено; задачи не дополнялись. Обязательные T017 browser/independent acceptance и T018 exact-SHA CI/release остаются отдельными воротами и до их выполнения не отмечаются закрытыми.

## Проверки установленной версии и выпуска

Ожидают выполнения на точном коммите: GRAF Dev build/promote/smoke, фактический браузер 320/390 и обе темы, окончательное независимое ревью, PR CI и замороженный release-full, CD, installed nginx и production synthetic smoke. Локальные тесты не заменяют эти доказательства.

## Совместимость и старые пути

Legacy Impact: remove — bearer invitation больше не создаёт session; legacy magic endpoint отвечает отказом для безопасной обработки прежних писем. Ранее принятые full_meeting ACL сохраняются по существующему контракту. Новые legacy aliases/dependencies/services не добавлялись. Публичные подписанные macOS артефакты выпуск сервера сохраняет; native route policy уже допускает meeting share/settings маршруты.
