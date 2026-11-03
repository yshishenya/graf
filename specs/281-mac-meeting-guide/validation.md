# Доказательства F281

Проверены: public/download.html (macOS 14.5, universal installer); docs/current-product-status.md (F090 upload, F113 speakers, F120 export и текущий native Record/Stop).

Приложение и звонки в сервисах этим материалом не испытывались. Обещания совместимости и точности ограничены. Новый шаблон использует существующий public renderer/_meta; protected templates не меняются.

Focused disposable PostgreSQL: 28 passed. Начальный тест нашёл условный #price, отсутствующий при fail-closed тарифном блоке; заменён стабильной ссылкой главной. Production registrations/payments/fixtures не использованы.

Mobile Chromium 360/390/768: document scrollWidth равен viewport width, один H1, честный Mac CTA; screenshot reviewed. Exact-SHA CI ожидается. PostHog ingestion не является условием публикации руководства.
# Исправление после полного CI

Полный CI кандидата `628812e6ff1b6c50953542fcfcdbe1654e8ef57c`, run 36777124979, завершился FAIL: общий контракт пользовательских текстов запрещает букву «ё» в новом шаблоне руководства. Исправлены только варианты «ё» → «е» этого шаблона, без изменения смысла, главной, download, политик или аналитики. Локально `test_copy_convention_contract.py`: 65 passed; `git diff --check`: PASS. Этот результат не заменяет обязательные checks исправляющего PR и новый полный release gate.
