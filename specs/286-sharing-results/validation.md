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

## Проверка развернутого Dev и найденная совместимость

- GRAF Dev exact SHA `664886c3b232484a51ab28be0f57c73837196fcd`: штатные build/promote и полный smoke PASS; миграция 0103. Холодная пара PostgreSQL/MinIO сохранялась harness до допуска новых writers. Предыдущая попытка безопасно восстановила старую версию при несовместимости настроек Dev: внешние приглашения включены при выключенной реальной почте; исправлено без ослабления Settings guard.
- Синтетическая встреча в личном пространстве: фактические open dialog, две вкладки, preview выбранного документа, create/copy link, закрытие и возврат фокуса на «Поделиться», публичный документ и добровольный CTA. Reader работает без JavaScript; no-JS owner form доступна. Настройки: ASK включен, ни одного AUTO правила по умолчанию, global pause и точечное управление представлены.
- На ширине 320 обнаружено переполнение кнопки добавления получателя. Исправлено нативной CSS grid; требуется повторная actual проверка нового SHA. Anonymous reader использовал навигацию кабинета: заменено узким документным shell с одной добровольной CTA; rendered contract + UI/no-JS 7 passed (5.24s), Node state tests PASS.
- Дополнительный CI выявил устаревший schema head и неполный identity FK inventory. Историческое согласие, адресаты и AUTO authority не перепривязываются при объединении; 19 соответствующих unit/runtime checks PASS.
- Отдельная app-role регрессия выявила необходимость каскадного переноса области публикации и delivery graph. Миграция 0104 и явный flush родителя исправляют граф, включая recipient rows без meeting_id. Реальная app role без SUPERUSER/BYPASSRLS: неверный merge context закрыт; confirmed merge, original data/states/tokens preserved; pending старого владельца отменяется без Postal. Связанный набор merge/comments/delivery/deletion: 53 passed, 39.46s. Старые URL с прежним workspace после merge закрываются, актуальную ссылку получает новый владелец.

## Окончательная проверка интерфейса и независимое ревью

- Исходный SHA `30ca64ec7319ce66aca675b9a23b6c6736edcfe1`: штатные GRAF Dev build/promote/smoke PASS, migration 0104; smoke подтверждает exact_source_sha, установленное приложение, backend/frontend, PostgreSQL/MinIO/Temporal и оба processing/media workers. Предыдущий source checkout сохранен для штатного отката.
- Реальный браузер исправленного окна: 320/390, светлая/темная темы. Строка адресата помещается; измерение dialog width 286, scrollWidth=clientWidth=284, выходящих за правую границу input/button/select нет. Вкладки ArrowLeft, Escape и возврат фокуса на «Поделиться» подтверждены. Preview показывает сохраненный выбранный документ.
- Реальный anonymous reader: нет cabinet-sidebar, ровно один CTA «Начать со своей встречи», document.scrollWidth равен viewport320 и390. Светлая/темная темы и чтение без JavaScript PASS. Owner no-JS form содержит получение/отключение ссылки и отправку почты. Temporary script/media/viewport overrides сброшены, оформление аккаунта возвращено на «Системная».
- Настройки после загрузки: ASK checked, pause unchecked, ни одной включенной AUTO встречи. В единственном `/Applications/GRAF Dev.app` реально открыты синтетическая встреча и окно двух способов, нажато «Скопировать ссылку» → «Ссылка скопирована». Нет реальной записи/частного содержимого в проверке.
- Независимое read-only review этого SHA: PASS, HIGH/MEDIUM0. Рецензент отдельно запустил merge+UI/no-JS через изолированный PostgreSQL runner: 8 passed,7.10s. Его результат не складывается с основным набором53passed.
- Почта/partial/unknown, AUTO guard/cancel/deadline и сбои транспорта проверены автоматическими mock/интеграционными наборами и Node state test. Реальная доставка в чужой почтовый ящик не выполнялась и не утверждается.
- Эти проверки закрывают T017; exact-SHA GitHub CI, замороженный release-full, рабочий ingress и production smoke остаются T018.

## Замороженная проверка, не разрешившая выпуск

Первый frozen candidate `rc-20261005T235931Z-f3b87b44222a`, source `cd9c5b2bb7d5d499aa02ac7b08371e8c2f804fe0`, GitHub release-full `37391541791`: FAIL. Статика/governance, strict PostgreSQL/performance и macOS проверяются отдельно от восьми серверных частей. Серверные части обнаружили PostgreSQL-only нарушение миграции, пользовательскую орфографию и устаревшие contracts/inventory/OpenAPI, включая browser comments selector. Кандидат штатно оставлен без выпуска, production не менялся. T020 добавлена для всех обнаруженных замечаний; обязательные проверки не обходятся и failed кандидат не переиспользуется.

T020 focused evidence: PostgreSQL-only/Compose/independent-login/migrations/runtime — 60 passed32.68s; interface/accessibility/theme/legacy-comments — 75 passed71.05s; copy convention — 74 passed0.13s; legacy-comments real HTTP/PostgreSQL/browser — 1 passed14.43s. Наборы не суммируются. Auth/RLS runtime не ослаблены; удалена только sqlite_where, revision type declarations и устаревшие ожидания контрактов согласованы с действующим интерфейсом.

T020 accepted-slot/candidate contracts:44passed32.63s; exact runtime OpenAPI drift:10passed8.64s. Canonical YAML добавляет11путей и6схем, не удаляет прежние пути/схемы и сохраняет порядок ключей. Действующая регрессия проверяет deprecated candidate preview410, candidate-only sharing409, current pinned accepted при новом candidate200/no-store без candidate текста. Первое full macOS PASS, server full FAIL не переиспользуется.


Второй frozen candidate rc-20261006T003217Z-ec639d836515, source355a743a26cbd643b5b42315dd996d1fe9dc9cf6, release-full37394531573: семь серверных частей, strict PostgreSQL/performance и static/governance PASS; shard7 выявил единственное устаревшее буквальное ожидание «ее/истек» после принятой нормы орфографии. Отказ выпуска сохраняется. Исправляется только ожидаемый текст test_recording_share_invitation_contract; все проверки статуса, недоступности, секретов и почтовой reservation fence сохранены. Runtime и установленный GRAF Dev47ea не меняются. Поиск всех потребителей этой фразы подтвердил один устаревший assert; соседние browser problem checks остаются в отдельной проверке.

Отдельная проверка окончательной орфографической регрессии: invitation contract + browser problem responses + copy convention — 90 passed,6.35s через изолированный PostgreSQL runner, контейнер удален. Ruff, git diff --check, Spec Kit governance PASS. Git diff относительно проверенного Dev47ea по apps/server/src и apps/macos пуст: продуктовый код и установленное приложение не изменены.

## T021 — исправление очистки после production

Root cause: раннее удаление track_artifacts до позднего workspace удаления storage_reservations. В общем helper добавлены21строки: artifact parent FOR UPDATE, ранний meeting+workspace reservation delete и optional inventory. Полные user/tenant/smoke guards сохранены. Реальный PostgreSQL focused cleanup/deadlock/context/unit набор:25passed1.19s, штатный изолированный runner5с с удалением контейнера. Новые тесты проверяют полную очистку связанного/несвязанного reservation графа, неизменность обычного соседа и concurrent INSERT из другого workspace, блокирующийся до23503 после удаления выбранного родителя. Ruff/diff PASS; runtime code не подменялся. T018 остается открытой до нового полного кандидата, CD и повторного production cleanup.

Независимое read-only T021 review PASS, открытых HIGH/MEDIUM0. Рецензент подтвердил ограничение данных и parent-lock; production cleanup отдельно остается T018.
