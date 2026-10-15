# Независимая браузерная проверка F280 FR-021–023 / SC-009

Дата: 2026-10-02. Рецензент: `provider_rejection_requirements`, отдельное задание browser review. Рабочая копия: `/Users/yshishenya/.codex/worktrees/release-f280/crisp`. Lane: read-only review актуальной реализации `high-risk-product`. Изменён только этот временный отчёт; повторные тесты, платежи, сообщения, GitHub, коммиты и выпуск рецензентом не выполнялись.

**PASS в проверенной синтетической области. CRITICAL0/HIGH0/MEDIUM0/LOW0 новых конкретных замечаний.** Прочитаны три production-файла и оба браузерных harness-файла, дополнительно существующая доступность/JS-off матрица и HTTP отрицания. Логи ведущего агента прочитаны после окончания; незавершённый WebKit не был выдан за PASS. Хеши всех пяти целевых файлов одинаковы при начале и завершении чтения.

## Фактические результаты ведущего агента

| Лог | Подтверждённый результат |
| --- | --- |
| `/tmp/graf-f280-provider-browser-chromium-root.log` | 8PASS,164.24с; focusedpass и isolated container removed |
| `/tmp/graf-f280-provider-browser-webkit-root.log` | 8PASS,233.14с; focusedpass и isolated container removed |
| `/tmp/graf-f280-provider-accessibility-chromium-root.log` | 16PASS,33.97с |
| `/tmp/graf-f280-provider-accessibility-webkit-root.log` | 16PASS,44.48с |

Оба browser-лога имеют collectioncount8 и один digest `5aa773da6b14d426cc012272836ddff4ae7b256a008980b7f134dd4594fcb1c1`. Шесть новых случаев: recurring/generic/uncertain×320/1280; две прежние verified/unverified цепочки. Отчёты не складывают число случаев с количеством внутренних утверждений и не выдают fixture за реальный путь.

## Смысл проверок и вывод

- Python bridge пропускает реальные байты браузерной формы и headers через штатный ASGI TestClient и отдельную PostgreSQL. Он не рендерит fixture, не следует303 и очищает TestClient-cookiejar перед/после запроса. Сессионный файл0600 содержит только синтетическую сессию, удаляется в finally; URL/формы/headers не логируются. TransportMock стоит только у адаптера YooKassa; внешний провайдер не вызывается.
- Настоящий DOM раскрывает промокод, вводит синтетический код, отправляет preview и принимает свежую годовую цену9000₽/будущую10000₽. Оферта выключена, recurringTrue; Space/Enter выполняют начальный start. Runtime `_request` получает exact403 либо соседний generic403/503; Python проверяет один operation+invoice/POST и снимкиTrue.
- На status и двух reload конкретный отказ показывает «Не удалось начать оплату»/«Оплата не началась», подсказку manualFalse и «Вернуться к оплате». Generic403 показывает общий отказ и «Попробовать снова», без выдуманной recurring-причины. Старый query provider_unavailable не перекрывает достоверный отказ; raw provider text не виден.503 остаётся manual_resolution/«Проверить статус», без retry/new checkout form. Число start остаётся1 при всех GET/reload.
- Retry — существующая ссылка сcycleyear, получает keyboardfocus/Enter. Новая форма сохраняетTrue и year, оферта непринята, quote отличается от старого. Два reload не меняют режим и не отправляютPOST. Расходованный promo draft не возрождается: цена10000₽, кодпустой; это явная граница FR-018, а не потеря действующего выбора при обычном refresh.
- Только Space на recurring вручную выбираетFalse; off-summary показывает отсутствие следующего автоматического списания. Новая оферта принимается Space; Enter создаёт ровно второй явныйstart. Нативное тело не содержит recurring_consent, содержитoffertrue/cycleyear/новыйquote. Существующий сервер трактует omittedoptional какFalse; SQL проверяет новые boolFalse snapshots и отдельныйidempotency, прежние снимки операции остаются byte-equivalent. Provider payload последовательность строго[True,False], созданный fake-payment только1. Следовательно automaticPOST/automaticFalse в проверенной цепочке отсутствуют.
- SQL на каждом последующем bridge-запросе подтверждает фактические состояния: rejectedcanceled/no provider_id, promotionreleased; uncertainmanual/reserved; общий счет/operation count равен числуdispatch. Это больше, чем проверка текста одного fixture.
- Старый403 безreason и malformed/schema1/bool/stringHTTP/bound/unknown/mismatchedinvoice покрыты самостоятельными HTTP отрицаниями в `test_billing_review_regressions.py`; текущая браузерная generic403 создаёт новую запись безspecific reason. Это разные виды доказательства, здесь они не названы одним DOM-сценарием.
- На320/1280 реальные страницы не имеют общей горизонтальной прокрутки; годовой retry, оферта, checkbox и submit управляются клавиатурой. Существующий accessibility suite дополнительно проверяет темы/масштаб/фокус и единыйstatusregion. Новая status-ветвь использует прежниеbutton/notice/card primitives без CSS или нового контроллера.
- JS-off подтверждён существующим accessibility suite: native required offer предотвращаетPOST; после ручнойоферты true/false сериализуются корректно и единственныйPOST перехвачен. Это **fixture/native-form proof**, не полный JS-off HTTP→SQL→provider-error путь. Различие соответствует документированной границе: новый status/retry работает сервернымHTML, False отправляется обычнойHTML формой; перенос предпочтения через навигацию безJS не обещан. Не выдавать этот result за полную JS-off финансовую приёмку.
- Прежние verified/unverified DOM-цепочки повторно проверяютmonth/year, valid/invalid/replace/remove, дваreload/back/return, две вкладки/исходныйexpiry, verifiedreceiptguard и устаревшуюоферту409 с сохранённымFalse. Таким образом новый error-mode не заменил широкую прежнюю матрицу.

## Хеши текущего проверенного source (SHA-256)

| Файл | SHA-256 |
| --- | --- |
| `apps/server/src/twobrain_rec_server/billing/yookassa.py` | `5988391c8a034cab8eb959e53f988eb0fef3b131ed5f845382792f61358157ce` |
| `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py` | `60151eb2a2c5d46bff9314eb5e10fbfd0eedeb939029d6fa4fbd9eab53a4dd12` |
| `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_operation_status_content.html` | `a2b98b75bb090e84a28e8c9e9479f909bc8fcf29e41e2f763a13d4e1c4437385` |
| `apps/server/tests/contract/test_billing_promo_refresh_browser.py` | `59852e799cc9a1a51a85d0a9c97108a3515c5ed5d40f5429c169a037a20a6eec` |
| `apps/server/tests/browser/billing-promo-refresh.test.cjs` | `fe25017951377b0e802c661a2c13b443e49d774c6a2253c163ae1173a1eb53b4` |

Дополнительный прочитанный JS-off/accessibility source: browser `1fd9e0ff39e4bc3180110eccaf92e8da1a9986522a7b7330f90fb4254faaa893`, Python `36bfbca53c8a56d8a00464f1185a0528869043889942057e47f2728d495fa3f5`.

Это синтетическое локальное доказательство настоящего browser→HTTP→SQL пути с fake-provider. Подключение автоплатежей у магазина, liveFalse acceptance, реальное списание/чек/банк/возврат, установленныйGRAFDev, человеческая приёмка/конверсия, exact-SHA CI иproductionrelease здесь не доказаны. Requirements/task final consistency также перечитана: T023–T025 связаны с#7414, analyze0critical/high, changelog сохраняет внешнее ограничение. Новых требований или рекомендаций расширить объём нет.
