# F280 — проверка результата оплаты, 3 октября 2026 года

Lane: high-risk-product / active Spec Kit slice; выпуск — release-deploy. Реальные платежи за пользователя не выполнялись. Начальная диагностика рабочей системы была только чтением: провайдер подтвердил один платеж на10₽, GRAF оставил pending/без grant. Причина — reconciliation выполнялся под app ролью с невидимыми через RLS событиями; штатная maintenance роль видела ожидающее событие. Идентификаторы/карточные данные/контакты в evidence не сохраняются.

## До реализации

Независимый requirements checklist17/0, анализ FR-031–038/SC-013 без critical/high, T029–T032 и issues7473–7476. Canon ensure/validate выполнены; каждый новый issue дополнительно проверен напрямую через validate_issue, ошибок0. Исторические задачи/платежная приемка F278 не переотмечены.

Root RED: `run_local_postgres_tests.sh --focused tests/integration/test_billing_clarity.py -k 'stale_continue or terminal_invoice or requires_linked_grant or historical_invoice' -q --tb=short --show-capture=no`: **7failed/3passed**, isolated container removed. Воспроизведены stale initial continue после succeeded/canceled/failed, terminal invoice с pending initial/storage operation, false success без grant и отсутствие paid period/title. Производство на момент RED неизменно.

После route correction: тот же runner с `-k 'stale_continue or terminal_invoice or requires_linked_grant'`: **9passed**, isolated container removed. Исторический period/title еще ожидает template/controller/browser реализации, это не итоговый PASS.

Дальнейшая browser/worker/role/общая матрица и независимые обзоры будут добавлены после выполнения. Исторический промокодный Full/выпуск не подтверждает новый код.

## Реализация и целевая регрессия

Сервер показывает успех только для succeeded invoice/operation и связанного права этой покупки. Оплаченный срок берется из grant и сохраняет исторический результат после окончания подписки. Завершенный invoice/operation блокирует stale continue до изменения actor; новый платеж не создается. GET остается чтением, protected POST/CSRF/rate/owner/tenant сохранены.

Общий focused PostgreSQL набор: `test_billing_clarity.py`, `test_billing_purchase_journey.py`, `test_billing_promo_refresh.py`, `test_billing_money_path_e2e.py`, `test_billing_ui.py`, `test_billing_clarity.py` contract, `test_cabinet_static_assets_contract.py`, `test_billing_security.py`, `test_billing_safety_contract.py`: **389 PASS /214.28с**, isolated container удален. Первая попытка186/2fail выявила два прежних success fixtures без grant; они дополнены честным grant только для paid сценариев, missing-grant negative tests сохранены. Final log `/tmp/graf-f280-payment-root-regression.log`.

После последнего исправления aria-live сравнение нормализованного пользовательского текста сохраняет объявление новой ошибки и подавляет только одинаковое ожидание. `test_billing_ui.py` + `test_cabinet_static_assets_contract.py`: **129 PASS /5.12с**; `node --check` PASS. Независимый reviewer закрыл UI-R1/R2/R3 по actual source. Worker evidence: [validation-payment-worker.md](validation-payment-worker.md),25 unit/contract и19 PostgreSQL role/replay PASS; реальная app-role причинная ошибка до fix подтверждена.

## T033 — передача очереди при выкладке и откате

Convergence выявил обязательный разрыв FR-038: CD останавливал только API, старый processing consumer мог пересечься с новым maintenance consumer. Append-only T033/#7478 добавлен до изменения CD; requirement scope прежний. Первый причинный order test **1failed** до forward stop. Recovery review выявил аналогичный разрыв при неудачном stop; actual Bash execution matrix до recovery fix **2failed/2passed**.

Окончательные forward/recovery tests исполняют извлеченные актуальные Bash blocks с stop exit0/23: после baseline включена защита отката; до up/compatibility остановлены processing+maintenance; при23 дальнейшего запуска нет. Новый forward stop строгий; recovery barrier при ошибке сообщает blocked/forward_fix_required и возвращает failure. Очередь/история/образы/миграционные ветви сохранены. Полный `test_deployment_readiness_gates.py`: **56 PASS /1.27с**; `bash -n` PASS. Независимый review UI-R4/R5 закрыт. Эта проверка не объявляет реальный Docker/production rollout состоявшимся.

Governance, changelog validator, Ruff touched production/server/root test paths и `git diff --check` PASS. Canon ensure/validate выполнены, прямой `validate_issue` для7473/7474/7475/7476/7478 ошибок0 (обычная выборка ограничена300). Browser/CI/Full/CD/runtime/live proof ожидаются отдельно.

## UI-R6 — безопасное чтение после timeout

Независимый обзор обнаружил, что GET recovery на обычный status мог загрузить новый документ и повторно начать automatic POST, пока прежний серверный запрос ещё выполняется. Причинный реальный PostgreSQL/HTTP test `local_status_recovery` до correction: **1failed/38deselected**, isolated container удален.

Recovery ссылка теперь использует existing status GET с `view=local`: это только проекция чтения, не источник финансового успеха. Она запрещает авто-проверку и POST-формы продолжения/проверки; pending получает повторное безопасное чтение. Первоначальный обычный return продолжает bounded auto refresh. Успех/grant проверяются тем же серверным путем. Root correction находится в T029/FR-034, без новых денег/прав/API/миграций. Actual timeout→click browser assertion передан отдельному исполнителю.

Первый recovery combined rerun дал91 PASS/1test-fail: новая проверка запрещала POST во всем документе и ошибочно учитывала скрытые формы настроек. Assertion сужен до payment main; production этим не менялся. Отдельный повтор recovery записывается отдельно, чтобы не выдавать неудачный прогон за92 PASS.

Final targeted `local_status_recovery`: **1 PASS/38deselected**,9.63с; isolated container удален. Таким образом combined91 PASS плюс исправленный targeted assertion1 PASS подтверждают весь набор без повторения91 неизменного теста.

## Pending continuation — browser causal RED

Независимый Chromium320 RED установил отсутствие вторичного «Вернуться к оплате» после настоящего provider pending: `_status_refresh_result` возвращает refreshed, template разрешал только unchanged. Minimal correction разрешает обе успешные проекции результата только при прежнем `can_continue_payment`; provider errors/terminal/service-gap/read-only recovery не получают продолжения. Платёж/сумма/номер не создаются повторно. Browser owner перепроверяет актуальный путь.

Связанный `test_billing_ui.py` после pending condition correction: **53 PASS**. Full browser до этой поправки: Chromium27 PASS/1 initial GET timeout5000ms (pending320, trace пустой); WebKit28 PASS. Это ошибка начального открытия стенда, а missing continuation причинно подтвержден отдельным continuation RED. Эти прогоны не объявлены совместным окончательным GREEN до повторной проверки измененного условия.

После one-line pending correction Chromium320/1280 **2 PASS** (32.08с), WebKit320/1280 **2 PASS** (35.97с), оба isolated контейнера удалены. Предыдущие full runs плюс целевой повтор покрывают все28 scenarios каждого engine; прошедшие неизменные сценарии повторно не запускались.

Service-review wording в FR-031/contract приведен к существующему честному «Оплата получена. Проверяем доступ»: непримененное право требует проверки, а не обещания автоматического подключения. Условия успеха/границы подтверждения не ослаблены. Это согласование формулировки вне выполнения read-only convergence, перед его окончательным результатом.


## Итог перед коммитом и переносом на master

Независимые source reviews: requirements (return_requirements), UI/payment safety (return_live_check, не автор UI), production/worker/CD (return_design, не автор production) — PASS, применимых открытых critical/high/исправимых medium0. Requirements checklist повторно прочитан:17checked/0unchecked, отметки root не менял. Матрица браузера: Chromium27PASS/1initial GET timeout, WebKit28PASS, адресный pending2PASS в каждом engine и a11y2PASS в каждом engine. Причинный missing continuation RED сохраняется отдельно. Полного Chromium28PASS не было. После переноса на актуальный master проверить затронутый CSS/focus; PR/Full/CD/live evidence еще не получены.
