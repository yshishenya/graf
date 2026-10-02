# Независимое review пути промокода F280

Дата: 2026-10-02. Reviewer: promo_flow. Рабочая копия: release-f280/crisp. Базовый HEAD `c4277f48b84e854774a87d0a452f1511a4a5a4bd`; проверялись незакоммиченные изменения, привязка ниже — к SHA256 файлов.

## Результат

Повторная независимая статическая проверка текущего пути обновления — PASS; открытых подтверждённых замечаний к продукту CRITICAL 0, HIGH 0, MEDIUM 0, LOW 0. M2 исправлено узким прямым once loadend исходного xhr и независимо перечитано по текущему хешу. Исторический finding и исправление описаны ниже. M1 исправлено; дополнительно перечитано исправление инициализации боковой панели при недоступном sessionStorage. Итоговая готовность этого среза пока **PENDING**: матрица Chromium имеет 26 PASS / 2 FAIL, WebKit 24 PASS / 4 FAIL; задержанный ответ после удаления исходного main и тайм-аут WebKit требуют завершённой диагностики и повторной проверки. Это не финальный PASS SC-011/SC-012 или разрешение пропустить T028. HTTP→SQL account regression независимо сверена: 6 PASS, финансовые regression 237 PASS, HTTP/domain/UI 205 PASS. Отчёт подтверждает перечисленные хеши исходников, но не заменяет tests/release/runtime gates T028.

## Историческое M1 — исправлено, повторная статическая проверка PASS

Первое чтение обнаружило, что `reserve_acceptance_budget` выдавал понятное сообщение ограничения аккаунта, но общий `ValueError` в initial checkout заменял его на `result=unavailable`.

В окончательных источниках `AcceptanceBudgetUnavailable(PurchaseError)` поднимается только для disabled/expired и exhausted budget; invalid existing reservation остаётся обычным PurchaseError. Initial checkout сначала делает rollback, затем только `isinstance(exc, AcceptanceBudgetUnavailable)` отображает в безопасный `account_unavailable`; template имеет фиксированное русское сообщение «Оплата для этого аккаунта сейчас недоступна. Обратитесь в поддержку.». Неизвестные ValueError и provider/network errors сохраняют прежний путь, raw exception не раскрывается. Проверка budget по-прежнему раньше commit/вызова провайдера, оснований обходить денежные ограничения не добавлено. Ссылка помощи присутствует в обычном footer. HTTP→SQL regression должен дополнительно подтвердить rollback/нулевые financial/provider effects для disabled/expired/exhausted.

Повторно проверено исправление focus после clear+Apply: если focus target относится к details, afterSwap раскрывает именно этот details перед focus. Скрытый после удаления кода Apply/input теперь не остаётся целью, недоступной клавиатуре; это не влияет на цикл и другой интерфейс.

## Проверенные свойства текущего кода

- FR-024: недоступность hash campaign (malformed/missing/disabled/expired/foreign) выдаёт сообщение о промокоде с действиями убрать/исправить. В UI поле открыто, связано с ошибкой через aria-describedby/aria-invalid; ошибочное предложение не даёт start form. Account initial route получает отдельный фиксированный публичный result; историческое M1 исправлено, см. выше.
- FR-025: form action/method сохранены, установленные HTMX target/select выбирают только main, outerHTML и hx-push-url=false. Разовая скидка и payment quote происходят из существующего server расчёта. После успешного swap текущая запись адреса заменяется только безопасным cycle month/year без промокода/quote/согласий. Новой записи истории код не создаёт.
- FR-026: память текущего документа хранит точный bool для user/workspace/session; change записывает False до потенциально бросающего sessionStorage. Ошибочная форма без checkbox не уничтожает память. На следующем новом checkbox global init восстанавливает значение; другой/неполный контекст память сбрасывает. Оферта снимается до запроса и новый server input без checked. Представление не является полномочием списания.
- FR-027: перед запросом снимается оферта, main получает aria-busy, все input/button отключаются; body capture блокирует денежную форму в checking/recovery. Single request охраняют document-local state и hx-sync drop. Timeout 15с, ошибки завершают ожидание, возвращают редактор и блокируют start до нового расчёта; 429 и invalid session имеют отдельные тексты. Поздний/неподключённый target не вставляется.
- FR-028: beforeSwap требует тот же xhr/state, подключённый прежний main, expected target, HTTP200, полноту и совпадение всех3 identity meta, checkout main. Login/unexpected/scope mismatch отбрасываются с явной ссылкой открыть оформление заново. Existing owner/CSRF/quote/receipt/pending/provider validation не изменяются этим транспортом.
- FR-029: новый код не меняет TTL подписи выбора300с, срок quote10мин, серверную применимость или денежное действие. В JS нет постоянного сохранения промокода; временный xhr/request и уже существующая form serialization не являются авторитетом скидки.
- FR-030: status/alert live regions, aria-busy, логичный возврат input/Apply/cycle, focusReady предотвращает global initBillingFocus jump. Деньги остаются обычным start form. Native fallback сохраняет обычную обработку внешних form-associated input/button и Enter. Нужны результаты реальных Chromium/WebKit для окончательного визуального/клавиатурного PASS.

## Сверка с установленным HTMX2.0.10

Проверен локальный vendored min.js, не предположение по другой версии. `dn` формирует FormData/submitter до beforeRequest, поэтому отключение controls после beforeRequest не удаляет уже собранные promo/action/CSRF параметры. BeforeSwap получает полный serverResponse до hx-select. При outerHTML установленный код сначала восстанавливает стандартный input focus, затем вызывает afterSwap на новых элементах; обработчик кабинета возвращает выбранный логичный focus после стандартного восстановления. SwapDelay по умолчанию0; нормальный afterSwap синхронно очищает billingPreviewRequest прежде afterRequest. После удаления исходной формы HTMX переотправляет afterRequest на подключённого предка, но pointer уже очищен: новый итог не переходит в recovery по успешному ответу. Global afterSwap initCabinet остаётся и переинициализирует renewal; local focusReady не позволяет ему увести focus.

Прочитаны первичные документы https://htmx.org/events/, https://htmx.org/attributes/hx-select/, https://htmx.org/attributes/hx-swap/. Никакая документация HTMX4 не применялась к локальной версии2.

## Выполненная проверка и границы

- `node --check apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js` — PASS.
- `git diff --check` — PASS на момент чтения.
- Полное новое browser matrix/HTTP/SQL runs не дублировались, поскольку отдельный worker владеет harness/tests. Видимая исходная inline regression проверяет настоящий server quote, неизменность window/document,0 navigation/history и False/offer; расширение failure/matrix ещё в работе.
- Это статическое независимое flow/accessibility review, не тест с экранным диктором, не человеческая приёмка, не реальная оплата/привязка карты/чек/банк/возврат/конверсия и не release/runtime evidence. Условие «пользователь точно оплатит» нельзя честно гарантировать тестами.
- Код, specs, plan, tasks, reviewer-owned checklists, GitHub, коммиты, выпуск и production не изменялись. Записан только собственный отчёт.

## Привязка к источникам

- `apps/server/src/twobrain_rec_server/billing/purchases.py`: `d03b4743c9ef29d12025e149b130260d3b2fd335a6eb4557cd063bccc9cfc66c`
- `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py`: `ba7db4c90ec19f85e114a276e3983619cf8e6321e45f1e992ab831532c5b75b8`
- `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`: `95f5d619f7cab0d70e1b604f0c6fccaba5ce47b91c756ae4fc9073ac75baeb34`
- `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_checkout_content.html`: `4b17d26ee11577eeb30a6d7788d4a8eafabfa1649a4dcef2613d34ebd10db3b0`
- `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/htmx-2.0.10.min.js`: `71ea67185bfa8c98c39d31717c6fce5d852370fcdfd129db4543774d3145c0de`


## Дополнительное независимое чтение после исправления sessionStorage

В initCabinetRail прежние getItem/setItem теперь защищены отдельно. Ошибка чтения оставляет прежний responsive default, ошибка записи оставляет ручное изменение панели доступным. Порядок initCabinetRail → initBillingRenewalChoice и регистрация глобального afterSwap больше не обрываются именно по этой причине. В памяти документа renewal False записывается до sessionStorage.setItem; два исхода обособлены. initBillingRenewalChoice сохраняет bool на страницах ошибки без checkbox, восстанавливает его только при том же полном ключе user/workspace/session, очищает память при изменённом или неполном ключе. Это не хранит принятую оферту и не заменяет серверную проверку списания.

Просмотрены текущие failure/guard сценарии. beforeSwap отвергает HTTP != 200, неверный ответ HTML/контекст, чужой xhr/current request и неподключённый прежний main. finishBillingPreview снимает текущий указатель прежде проверки isConnected; подключённый main переводит в ручное восстановление, блокирует start и снимает busy. Тесты матрицы -2 завершаются timeout ожидания наблюдаемого browser state/loadend. По одному этому результату нельзя заключить, что случилась неверная скидка, финансовый POST или изменение нового main; равным образом нельзя объявить все поздние ответы и предел 15 секунд доказанными. Исполнитель проверяет причину, исходники в рамках этого чтения не изменены.

Сверка журналов выполнена только на безопасные сводки, без включения исходных приватных логов:

| Набор | Подтверждённый результат | Значение |
|---|---|---|
| HTTP/domain/UI -domain2 | 205 PASS, 395.14с; очистка отдельной БД PASS | Понятные сообщения и существующие серверные ограничения |
| Account -account-green | 6 PASS, 101 deselected, 36.23с; очистка PASS | Disabled/expired/exhausted и отсутствие обхода удалением кода |
| Финансовые regression | 237 PASS, 446.56с; очистка PASS | Существующие финансовые ограничения |
| Chromium полная -2 | 26 PASS / 2 FAIL, 525.28с; очистка PASS | Обе ширины inline-guards: ожидание detached-late |
| WebKit полная -2 | 24 PASS / 4 FAIL, 633.85с; очистка PASS | Обе ширины inline-timeout и inline-guards |
| Текущее синтаксическое чтение | node --check и git diff --check PASS | Синтаксис не заменяет браузерное доказательство |

## Инвентаризация для сходимости текущего среза

Ровно 10 новых требований: 7 FR и 3 SC. Текущие T026–T028 уже покрывают реализацию, проверки и выпуск; новых дублирующих задач не требуется. Ниже статическое соответствие отдельно от незавершённого доказательства готовности.

| Требование | Решение плана / текущий источник | Статус текущего независимого чтения |
|---|---|---|
| FR-024 | Решение 5: purchases.py + типизированный account_unavailable в billing.py/template | PASS; понятный promo/account отказ, условия ограничения прежние |
| FR-025 | Решения 1/4: существующий HTMX preview + безопасный replaceState cycle | PASS по коду; 0 полных навигаций подтверждается только прошедшими браузерными случаями |
| FR-026 | Решение 2: память документа + scope + необязательный sessionStorage | PASS по коду после rail fix; оферта не переносится |
| FR-027 | Решения 2/3: busy/drop/15с/recovery/native start guard | PASS по текущему коду после direct xhr loadend; тайм-аут WebKit browser proof PENDING |
| FR-028 | Решение 3: xhr/context/target guard, существующие серверные guards | PASS по текущему коду: beforeSwap guard сохранён, M2 очистка state исправлена; browser proof PENDING |
| FR-029 | Решение 5 + сроки/совместимость: draft300с, quote10мин, деньги прежние | PASS; нового финансового источника или хранения кода в JS нет |
| FR-030 | Решения 1/6: фокус, live regions, native fallback, прежние стили | PASS по коду; экранный диктор/люди не заявлены |
| SC-010 | План проверки inline/native/False/storage/receipt на 320/1280 | Применимые обычные случаи проходят в -2; финальная матрица PENDING |
| SC-011 | План проверки delay/double/network/timeout/auth/context/late | PENDING по указанным шести browser failures |
| SC-012 | Общие public errors + три независимых текущих обзора | Сообщения PASS; итоговый общий PASS ждёт окончательных браузерных доказательств и актуальных verdict |

План содержит 6 нумерованных архитектурных решений, все сопоставлены: 1 транспорт и native fallback; 2 сохранение выбора и занятость; 3 проверка текущего ответа и восстановление; 4 безопасный текущий период в адресе; 5 public promo/account тексты без ослабления условий; 6 доступность и фокус. Дополнительные разделы «Сроки и совместимость» и «Проверки и порядок допуска» сохраняют прежние финансовые сроки/ограничения и T028. Billing.py расширен узко из-за подтверждённого M1, в соответствии с разрешённым исключением плана.

В constitution перечислены 7 основных принципов. Для этого среза проверены 5 применимых принципов (включая release obligation V), 2 остаются неизменными вне области вмешательства:

| Принцип | Применимость и соответствие |
|---|---|
| I Capture-First MVP Integrity | Не изменяется: аудиозахват/маршрутизация вне четырёх производственных файлов |
| II Visible Consent And User Control | Согласуется с сохранением видимого выбора True/False и явным денежным действием; специальные правила capture не переосмысляются как новые правила billing |
| III Plaintext Observability For Internal MVP | Применимые ограничения секретов/доступа сохранены: metadata scope не токен, в ошибках нет provider/raw exception, новый внешний получатель не добавлен |
| IV Deletion Truth And Lifecycle Accounting | Не изменяется: тексты удаления и артефакты встреч не затронуты |
| V Public macOS Distribution And Update Integrity | Обязательство T028: серверный выпуск должен сохранить прежние публичные подписанные байты; текущий обзор не доказывает публикацию |
| VI Spec-Driven Delivery With Testable Gates | FR/plan/checklist/tasks/analyze существующей F280; окончательные browser failures не приписаны PASS и выпуск остаётся T028 |
| VII Reference-Fidelity Product Design | Существующие стили и независимый код; фокус/ошибки/aria не должны ослаблять доступность; новых чужих ресурсов нет |

Итого: 10 требований / 6 решений плана / 5 применимых принципов + 2 неизменных. Открытых подтверждённых продуктовых finding 0 (M1/M2 исправлены); незавершённый validation gate 1 (SC-011 и итоговое browser evidence), состояние PENDING. F278/T011/T012/реальные деньги/конверсия остаются отдельно открытыми. Изменён только этот независимый отчёт.


## Историческое M2 — финализация запроса зависит от всплытия события удалённой формы (MEDIUM, исправлено в коде)

Повторное чтение установленного HTMX2.0.10 уточнило прежний вывод о detached target. В g.onload список In(r) вычисляется **в момент загрузки ответа**, а не до отправки запроса. Если исходный main вместе с preview form удалён до ответа, его родители уже не доходят до document.body. beforeSwap/afterRequest не попадают в обработчики cabinet.js на body. Для g.onerror/g.onabort/g.ontimeout обработчики HTMX также отправляют события на исходный r без независимой гарантии передачи на body.

finishBillingPreview умеет безопасно очистить указатель для detached state, но ему требуется вызов. Без гарантированного вызова billingPreviewRequest может навсегда остаться прежним state. Последующие preview в новом подключённом checkout main отклоняет beforeRequest, потому что billingPreviewRequest != null. Устаревший response не обязан изменить текущую сумму, чтобы это стало дефектом восстановления. Это исправимый MEDIUM FR-027/028 и SC-011, а не доказанный финансовый обход.

Рекомендуемое минимальное исправление для root: добавить финализацию через собственное событие исходного xhr (например, loadend/error/timeout/abort) с прежним state identity и идемпотентным finishBillingPreview. Успешный afterSwap должен успевать очистить state первым; detached fallback должен освобождать только старое состояние и не менять новый main/renewal/оферту. Нужна regression не только «старый quote не изменился», но и «после detached завершения новый preview разрешён». Тесты и код этого reviewer не изменяет.


## Повторное чтение минимального исправления M2

Текущий cabinet.js SHA256 `95f5d619f7cab0d70e1b604f0c6fccaba5ce47b91c756ae4fc9073ac75baeb34`. В beforeRequest сразу после присвоения billingPreviewRequest/state xhr добавлена прямая once подписка loadend → finishBillingPreview(state, true). Нового таймера, навигации, финансового действия или обхода beforeSwap нет.

Исправление соответствует причине finding. Событие исходного xhr не зависит от DOM-подключения preview form; loadend приходит после завершения ответа/ошибки/тайм-аута/прерывания. finishBillingPreview сначала сравнивает точную identity state с текущим запросом, затем очищает указатель, а уже затем проверяет state.page.isConnected. Поэтому завершение старого удалённого main освобождает возможность следующей проверки и не изменяет новый main, выбор автопродления или оферту. Поздний loadend предыдущего state не может очистить более новый запрос. Для обычного успешного ответа установленный HTMX и заданный outerHTML без swap delay выполняют afterSwap до loadend, afterSwap снимает текущий указатель; дополнительный fallback становится no-op. Для подключённого main, где успешный swap не произошёл, fallback переводит именно старую страницу в recovery и блокирует её start.

Статическое исправление M2: PASS. node --check текущего cabinet.js: PASS. Окончательное подтверждение нового кода в браузерах остаётся PENDING, прежние матрицы -2 относятся к исходникам до этого исправления и не объявлены зелёными. До нового evidence этот отчёт не подтверждает полный SC-011/SC-012 или release readiness. Reviewer изменил только собственный отчёт.
