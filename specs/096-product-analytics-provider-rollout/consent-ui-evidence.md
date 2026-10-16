# Consent UI: изолированное подтверждение 03.10.2026

Scope: продолжение draft PR7477 / issue7472, source `40a3606efe447ba9c710a69d3fb8fe941f155ab9`, high-risk privacy/auth/backend. Сохраняются pseudonymous IDs, отсутствие клиентского IP/content/replay/autocapture, proposal retention365. Production/config/credentials/MFA/TTL/purge не выполнялись.

## Подтверждено

- Существующие vendored CookieConsent UI, notice copy и категории используются без изменения общей `public/analytics.js`, landing/download и policies. В explicit режиме browser providers выключены; кнопки личного выбора связываются с authenticated `/explicit-context` → `/explicit-consent`.
- Only trusted all/necessary/save click пишет согласие. Hydration, сохранённая cookie, недоверенный click и HTML предыдущего аккаунта не дают нового согласия. Storage key относится к серверному псевдониму конкретного пользователя.
- Server ожидаемый псевдоним и актуальная acceptance version проверяются под user row lock. Cookie route применяет существующий CSRF. Отзыв допускается при stale copy/off/readiness; ошибку/потерю ответа UI честно показывает как неподтверждённый результат с повтором.
- Немедленный `pending` закрывает native gate. Каждое уведомление получает поколение синхронно; более старый async `changed` не снимает новый pending. Даже самостоятельный refresh не открывает gate во время неопределённого выбора. Bridge не передаёт разрешение или identity: native повторно получает authenticated серверный context.
- Разные действия сериализуются: revoke во время accept не теряется, последний выбор достигает API. Одинаковый pending выбор не размножает PUT.

## Проверки

`run_local_postgres_tests.sh --focused` explicit UI/API, explicit funnel unit/integration, PostHog wrapper, migrations и worker schema gate: **62 PASS**. Runtime использовал существующие зависимости, отдельный одноразовый PostgreSQL, существующие seeded auth session/device binding и текущие серверные маршруты. PostgreSQL удалён штатным cleanup после проверки.

Реальный headless Chromium рендерил штатный `/meetings` HTML и actual vendored library, переходил click → HTTP test adapter → настоящий FastAPI cookie-auth/CSRF → PostgreSQL → context readback. Adapter меняет только automation bot guard; fault injection/context mismatch помечены synthetic. Ни auth dependency, ни consent endpoint, ни DB запись не заменены заглушкой. Два реальных synthetic users имеют отдельные session/device bindings; account B начинает not_seen и принимает только собственным click, old A page не может изменить B, выбор B не меняет A. Проверены reload, unchanged save, revoke, stale version, context mismatch, отказ PUT, потеря ответа после настоящего commit, быстрый revoke. Дополнительная doubleclick регрессия выполнена отдельно после основного набора; её результат записан в PR receipt.

`swift test --package-path apps/macos --filter ProductActivationAnalyticsContractTests`: **30 PASS**, в том числе pending → ordinary refresh и older changed → newer pending → delayed old completion. Установка/запуск приложения, браузер пользователя, VoiceOver и GSC не выполнялись. Native установленный пользовательский путь этим набором не переаттестован.

`ruff check`, `validate-agent-context.py`, `check-development-process.py`, `validate-changelog-fragments.py`, `git diff --check` и JS syntax: PASS. Protected public subtree diff против source SHA пуст. Независимый read-only reviewer требований: consent6/0, minimal8/0; финальный code review после устранения гонок: новых P0/P1 нет. Reviewer-owned файлы основным writer не отмечались.

## Граница доставки

Provider в тестах synthetic fake; consent UI сам capture не делает. HTTP 200/`provider_accepted` не доказывают ClickHouse ingestion, provider deduplication, runtime no-IP/GeoIP или retention365. Эти критерии остаются BLOCKED, а T109 открыт. [Разрешённая попытка стенда](isolated-delivery-attempt.md) завершилась OOM на официальном bootstrap до capture; ресурсы удалены, T109 открыт. [План](isolated-delivery-plan.md) описывает границу следующего окна. Required PR checks проверяются отдельно на exact pushed SHA; локальные тесты их не заменяют.

Внешнее включение требует неизменённого notice legal mapping, актуальных backup/restore/offsite proofs, существующего доступа и MFA, отдельной secure secret-file wiring и retention assessment/action-time approval. Production остаётся выключен. D7/payment/refund вне scope.
