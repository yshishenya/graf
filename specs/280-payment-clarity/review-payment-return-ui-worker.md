# F280 — независимый обзор результата оплаты и порядка запуска

Дата: 2026-10-03. Проверка `code-reviewer`, только чтение исходников и запись этого отчета. Режим: high-risk-product + release-deploy. Проверяющий не автор `billing.py`, шаблона, контроллера и браузерных файлов; перенос обработчика сверки T030 авторский и не считается здесь независимым обзором своего кода. Production, GitHub, commits и checklist markers не менялись.

## Результат обзора исходников интерфейса

В проверенном срезе новых применимых critical/high/medium замечаний интерфейса не обнаружено. UI-R1/R2/R3 из `review-payment-return-ui.md` закрыты по текущему коду:

- Непустой ключ содержит user/workspace/session/invoice. Смена/потеря контекста блокирует дальнейшую автоматическую последовательность в документе. Перед вставкой ответа проверяются текущая страница, исходный target, единственный входящий main и обе session meta.
- Подавление повторной озвучки сравнивает нормализованный текст status region, после чего меняет именно `event.detail.serverResponse`; новый текст ошибки провайдера не подавляется.
- Подтвержденный счет и связанный grant обязательны для текста предоставленного доступа. Подписочный период берется из grant данного счета; исторический оплаченный счет не зависит от сегодняшней активной подписки. Отсутствие grant переводит экран к проверке доступа. Storage проверяет собственный grant.
- GET не получил запросов к провайдеру/денежных изменений. Автоматическая проверка вызывает существующий защищенный POST refresh. Перед устаревшим continue сервер повторно проверяет terminal invoice/operation; completed/canceled/failed нельзя вернуть к оплате.
- Один запрос, документный ledger, максимум6 автоматических попыток/60с, интервал начал≥10с, HTMX timeout15с; ошибки, скрытая/покинутая страница, измененный контекст и отсоединенный target прекращают проверку. После timeout предлагается локальный GET, следующий денежный POST блокируется. Abort не считается отменой серверной операции.
- Шаблон сохраняет обычную POST-форму с CSRF без JavaScript, основной результат «Оплачено» и «К встречам», оплаченный срок, закрытые сведения о платеже. Pending сначала предлагает проверку, продолжение существующего платежа вторично и только после unchanged.

Результат чтения не доказывает VoiceOver, отсутствие лишнего скачка фокуса или реальную матрицу браузеров. Существующие integration tests проверяют missing grant, исторический период, terminal continue и terminal invoice с еще pending operation.

## Браузерное доказательство на момент чтения

Прочитаны actual `billing-payment-return.test.cjs` и `test_billing_payment_return_browser.py`: настоящий HTTP→ASGI→PostgreSQL, синтетический provider, success case320/1280, сохранение document identity,1 document navigation,1 refresh POST, grant1, invoice/operation1, create1 и provider GET1; external requests запрещены. Статическое чтение не является результатом выполнения. Текущий snapshot файлов содержит только success case; остальные сценарии/темы/200%/JS-off/управляемое время должны быть подтверждены текущей полной матрицей отдельного исполнителя. Не повторял его выполняемые проверки и не записывал будущий GREEN заранее.

## Замечание к порядку выпуска — UI-R4 подтверждено

**HIGH, release HOLD до устранения.** `infra/scripts/cd-remote-runtime.sh:1152–1168` фиксирует baseline, останавливает rec-api, затем одним Compose up обновляет processing и maintenance. Явной остановки прежних processing/maintenance consumers до запуска нового maintenance poller нет. Для переноса существующей очереди это не доказывает отсутствие периода совместного потребления старой app-role регистрацией и новым maintenance executor. Это уже описанное UI-R4, не новый дубликат дефекта.

Минимальная рекомендуемая правка: заменить существующий checked stop rec-api после `runtime_mutated=1` на один checked `"${compose[@]}" stop rec-api rec-processing-worker rec-maintenance >/dev/null`. Baseline и `prompt_worker_was_running` оставить до stop, запуск candidate/verify/readiness оставить после. Не добавлять `|| true`; не менять queue/workflow/activity IDs. Такой stop включает старый maintenance и исключает смешанный запуск при его повторном обновлении. Если stop возвращает ошибку, существующий EXIT trap должен выполнить штатное восстановление, а новый up не начинаться.

Прочитаны `rollback_on_exit`, `restore_previous_services`, `restore_compatibility_runtime` и `restore_previous_safe_processing_runtime`: штатное восстановление включает processing+maintenance; `runtime_mutated=1` перед stop сохраняет этот путь при неудаче. Изменять rollback для данной минимальной правки не требуется по прочитанному коду. Нужен узкий regression порядка baseline→checked stop всех3→runtime_up→candidate/role/readiness и проверка после выпуска: прежняя app-role регистрация отсутствует, maintenance является единственным текущим consumer. Исторические Temporal poller записи не равны живому процессу: сверять container/runtime identity и актуальность наблюдения.

Это исполнение FR-038 внутри F280, без новой очереди, расширения RLS, ручного grant или нового платежа. Исправление скрипта и rollout принадлежат root; здесь рекомендация, не примененная правка.

## Проверенные snapshots SHA256

| Файл | SHA256 |
|---|---|
| cabinet/web_routes/billing.py | dc9960dc90adf18b71ca510395aa104a0cd54f9a75c4dc3494ec7ad56c434840 |
| cabinet/templates/cabinet/pages/billing_operation_status_content.html | 63ad75e182bba7543422472cd65517abd9fb32ebd6399a2d92c51602489c989e |
| cabinet/static/cabinet/cabinet.js | 7946ccd9b6498808034f3ac2fd102e8e0ba046bb2f6dd6c4b36bb91cf6774a7f |
| tests/browser/billing-payment-return.test.cjs | ffa6c8efe5c9e52120c2eab53e9f1b1c2e14566bab807cf84d8d372e8d74edf6 |
| tests/contract/test_billing_payment_return_browser.py | 48d3b170d7e6d1c8ab1bd29506f8992a523ee9b303e64e0403c15035f5bd2d6b |
| infra/scripts/cd-remote-runtime.sh | d6378cbd8d28e44ff10ab091c025bfc9cf0a2e9cd2c42baa58bae945e7037a05 |

Cabinet paths relative to `apps/server/src/twobrain_rec_server/`, tests relative to `apps/server/`. При изменении этих файлов обзор требует адресного обновления по измененному срезу.

## Границы допуска

UI source review PASS; release HOLD по UI-R4 и до окончательного выполнения обязательных browser/release gates. Живая сверка настоящего платежа разрешена отдельным заданием после выпуска и здесь не выполнялась. T011/T012, F278, банковское зачисление, возврат, recurring и человеческая конверсия этим обзором не закрыты.


## Повторный обзор исправленного выпуска — R4/R5 закрыты

Actual forward rollout теперь после baseline/prompt metadata и `runtime_mutated=1` выполняет strict stop rec-api/rec-processing-worker/rec-maintenance до sync_public_download и runtime_up. Actual `restore_previous_runtime` начинает со strict conditional stop processing/maintenance; stop failure возвращает1 и blocked/forward_fix_required до любой ветки запуска. `rollback_on_exit` сохраняет исходный nonzero exit. Ранее best-effort cleanup далее не возобновляет consumers. R4 из этого отчета и recovery R5 из `review-payment-return-ui.md` закрыты по текущему коду; новых замечаний данного среза нет.

Независимо прочитаны причинные Bash execution tests stop0/23 для forward fragment и функции recovery; `/tmp/graf-f280-rollout-green.log` содержит56 PASS/2 existing warnings/1.27s. Исполненный здесь `bash -n infra/scripts/cd-remote-runtime.sh` завершился0. Повторять suite без нового изменения не требовалось. Source bindings: runtime script SHA256 `48428a85cb326de2f6a1ebb48992eff554978ab93a997693e47a66c81519b57c`; deployment gates tests SHA256 `04e8803b652cab8c3e1187f0dc41ba7342638db249e578a48901115520f612e1`.

Source/rollout review PASS, применимых открытых critical/high/medium0. Исторический HOLD выше заменен этим итогом только для R4/R5; обязательные browser/CI/CD/live доказательства сохраняются отдельно.

Подготовлены, но не исполнены в production, временные `/tmp/graf-f280-paid-return-observe.py` и `/tmp/graf-f280-runtime-return-observe.py`: PostgreSQL READ ONLY + rollback; только provider GET существующего payment; вывод только состояний, timestamps, счетчиков и binding booleans, без invoice/provider/user/session/card IDs, контактов, URLs и credentials. Проверка оплаченного срока и суммы привязана к существующему счету, без создания/сверки/ручного grant. Receipt registration и число metadata observations выводятся отдельно и не доказывают доставку чека. Runtime probe проверяет actual session/current role, row_security/superuser/BYPASS/maintenance predicate; Temporal DescribeTaskQueue читает workflow/activity pollers и age/freshness120s. Старые сохраненные poller records не объявляются текущими; fresh processing после остановки надо сопоставить с timestamp выпуска/container state, при необходимости перечитать после истечения120s без активности сверки. Временные скрипты прошли только локальный py_compile. Ожидание root deploy GO; рабочая система этим этапом не читалась и не изменялась.


## Адресный повторный обзор локального восстановления — UI-R6 закрыт

Actual routes/template перечитаны после изменения root. GET `?view=local` передает `read_only_recovery=True`, подавляет can_continue и не добавляет денежных/provider вызовов; template задает auto_check false независимо от pending/can_refresh, вместо refresh POST показывает GET с тем же `?view=local`, recovery link тоже сохраняет этот параметр. Ни refresh, ни continue POST в status main не остаются; новая document ledger без form не запускает POST. Финансовый источник результата прежний: query меняет только представление, не превращает pending в paid. Подтвержденный succeeded/grant по-прежнему показывает успех и оплаченный период.

Secondary continuation после защищенной успешной проверки теперь разрешена для `status_result in [unchanged, refreshed]` только при server can_continue. Это исправляет допустимый still-pending payment после успешного provider GET; terminal invoice/operation и read_only view сервером исключены. Незавершенность не выводится из result query; сама stale POST continue сохраняет авторитетную проверку.

Перечитан actual PostgreSQL test `test_local_status_recovery_never_restarts_payment_check`: pending page normal auto true, local auto false/no status POST form/no ложного success, invoice/operation counts неизменны. `/tmp/graf-f280-local-recovery-targeted-green.log`:1PASS/38deselected/9.63s, isolated container removed. Более ранний общий log local-recovery-green содержал1FAIL/91PASS из-за слишком широкого assert по всей странице, который находил unrelated settings POST; actual test теперь проверяет только status main, targeted final PASS заменяет этот конкретный fixture FAIL и не объявляет общий suite перепройденным. Actual browser timeout branch прочитан: после local recovery auto=false, обе status forms отсутствуют и refreshPosts не увеличивается за наблюдение recovery; actual pending branch проверяет secondary continuation. Весь обновленный browser suite здесь не выполнялся и его итоговые числа не приписываются этому обзорщику.

Новых applicable critical/high/medium findings0; UI-R6 и continuation source PASS. Route SHA256 `f924f09e633b82bb66b12dc08f0ffb3259a08670891c32377f4c7d0ad3d0a1c6`; template SHA256 `10d2a66d6bb2d18e4c111acae91cf47cae4893548e4919b9965592b36ee240f3`. Обзор ограничен измененным срезом, не повторная независимая проверка авторского backend. Production/tasks/commits не менялись.

Временные скрипты сохранены: `/tmp/graf-f280-paid-return-observe.py` (SHA256 `948a379d694b871817073d47d2a82acad0553a33dee18fbae71e10577b045c1d`), `/tmp/graf-f280-runtime-return-observe.py` (SHA256 `869d4a1f1d652ed2d4da57cb194b982c16d771013cd428faeb02e1ef36914b63`). Подготовлен только локально `/tmp/graf-f280-postdeploy-return-readonly.sh` с точными командами чтения через SSH/docker exec Python stdin: обнаруживает ровно1running Compose service container; выводит safe service/start time, затем actual app-role probe, maintenance-role+Temporal DescribeTaskQueue и существующий payment GET. `bash -n` этого wrapper PASS; он не запускался. Команда после отдельного root deploy GO: `bash /tmp/graf-f280-postdeploy-return-readonly.sh`. GO все еще не получен.


Дополнительно перечитаны `/tmp/graf-f280-pending-continuation-chromium-green.log` и `/tmp/graf-f280-pending-continuation-webkit-green.log`: в каждом2PASS для pending320/1280, provider-controlled real HTTP/ASGI/PostgreSQL; отдельное выполнение принадлежит browser owner. Это подтверждает адресное исправление secondary continuation в обоих движках, не весь release gate.
