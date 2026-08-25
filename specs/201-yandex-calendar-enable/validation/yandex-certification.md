# Y201: сертификация Яндекс Календаря

Дата проверки: 2026-08-25  
Проверяемый commit: `e123f15a`  
Базовое правило: неполная матрица не считается сертификацией. Для этого
rollout владелец продукта явно подтвердил включение Yandex с принятием
остаточного риска по embedded macOS сценариям.

## Матрица

| ID | Поверхность | Результат | Metadata-only evidence |
|---|---|---|---|
| Y201-01 | Browser | PASS | Local development, viewport 939x1074: форма подключения Яндекса открывается и содержит только поля логина, пароля приложения и безопасное имя подключения; raw secret не отображается. |
| Y201-02 | Browser | BLOCKED | Реальный invalid-password submit в этом прогоне не выполнялся: передача credential в форму требует отдельного подтверждения непосредственно перед вводом. |
| Y201-03 | Browser | BLOCKED | В существующем локальном источнике наблюдаются 2 календаря, но повторная live-проверка dedicated test account в этом прогоне не выполнялась. |
| Y201-04 | Browser | BLOCKED | Текущее состояние безопасно показывает `2 из 2 выбрано`; сценарии zero/one selection проверены targeted integration suite, но UI-переключение пользовательского источника не выполнялось. |
| Y201-05 | Browser | PASS | Manual sync завершился `completed`; источник актуален, выбрано 2 из 2, на странице встреч отображаются 2 безопасные строки без названий и ссылок. |
| Y201-06 | Browser | BLOCKED | Повторное подключение с credential не выполнялось, поэтому отсутствие duplicate active source live-сценарием не подтверждено. |
| Y201-07 | Browser | BLOCKED | Disconnect не выполнялся: это меняет пользовательское состояние и требует отдельного подтверждения. |
| Y201-08 | Embedded macOS | BLOCKED | Installed GRAF visually checked: Yandex remains `Скоро`, connected calendars absent; native Record/Stop boundary remains available. Full connected/invalid/disconnect repeat is not certified. |
| Y201-09 | Browser + Embedded macOS | BLOCKED | Browser reload preserved the safe upcoming projection (2 hidden rows) without credential/raw-provider-error echo; embedded session-refresh matrix is not complete because Yandex is not connected there. |

## Automated evidence

- Targeted first pass: 125 passed; 19 checks could not start without disposable PostgreSQL URL.
- Corrected targeted pass with `run_local_postgres_tests.sh`: **214 passed**, 2 warnings; isolated PostgreSQL container was removed by the runner.
- Native targeted Swift suites (`DesktopCalendarReminderTests`, `DesktopUploadClientTests`, `RecordingMetadataResolverTests`): **78 passed**.
- `git diff --check`: PASS.
- Production health: live 200, ready 200.
- Production unauthenticated calendar API: 401; no provider catalog exposed.
- `REAL_E2E_CERTIFIED_PROVIDER_FAMILIES` remains empty; production Yandex remains fail-closed.

## Release override

Владелец продукта явно подтвердил включение `caldav_yandex` в production
несмотря на BLOCKED-сценарии Y201-02, Y201-03, Y201-04, Y201-06, Y201-07,
Y201-08 и часть Y201-09. Это release-исключение, а не замена real E2E
сертификации; остальные провайдеры остаются fail-closed.

## Decision

Y201 evidence is **incomplete**, but the explicit owner-approved release
override authorizes `caldav_yandex` in production. Remaining embedded scenarios
must be completed in the follow-up certification pass; if a regression appears,
remove only Yandex from the certified-provider set.
