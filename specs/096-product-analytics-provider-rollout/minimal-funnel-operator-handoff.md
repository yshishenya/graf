# Операторский переход к минимальной воронке (предложение, не выполнено)

Режим пользователя: явные события и псевдоним user, без клиентского IP/содержимого/автосбора/replay/directdesktop;365дней. Это псевдонимы, связуемые с аккаунтом внутри ГРАФ, не необратимая анонимизация.

## Выполнено в изолированном коде

Authenticated explicit-context/consent/events, запись согласия и первых вех на существующейuser row с RLS/CSRF, серверныйuserID, default-off. Desktop refresh/reset, receipt200 отдельно от provider ack и ingestion; stableUUID на retry. Исторический ingest с client claim в minimalmode закрыт. Product settings/provider modes не включены в production.

## Недостающие операционные доказательства

По отдельному read-only ops report02:13UTC2026-10-03: известные restore receipts18July вне30дней; documentedbackups/scripts/timers/receipts на проверенном пути не установлены, offsite success не подтверждён. Иные backupmethods не проверены. Два существующихadmin, подтверждённыйTOTP/orgMFA не обнаружены. Это повод проверить/выполнить установленный контроль, не создавать новыйдоступ или объявлять полного отсутствия резервных копий.

Оператор входит обычным поддерживаемымlogin существующего self-hostedPostHog. Не создавать PAT/grant, не переносить пароль/ключ/cookies через чат или чужую БД. MFA/security steps выполняются существующимиоператорами с отдельным action-timeapproval. Capturekey будет доступен только собственномуserver через существующий защищённыйsecret-file путь после отдельногоsecureapproval; management и capture права различаются.

## Конфигурация после доказательств

Предлагаем explicit_funnel_enabled=true только вместе с существующим approved provider gate; provider_enabled/live_provider_delivery остаются off до personalconsent/nativepath и isolatedingestionproof. Autocapture/webdirect/desktopdirect/directegress/replay/Yandexoffline=false. Существующуюверсию consent не изменять; legal/privacy reviewer сопоставляет реальный текст и новуюкатегорию, а не ставитфлаг по предположению. Operatorapproval не согласие человека.

В envexample новая настройка commentedfalse, Compose defaultfalse. Сначала migration nullablecolumn без backfill consent, затем контракт API/native. ПубличныйmacOSпакет нельзя подменять тестовойсборкой; отдельныйDeveloperID/notarization/release gate остаётся.

## 365дней не означает немедленное удаление

Opsreport: projecteventretention84months/noTTL; прежнийAPIfailure касался replay90days, не event365days. Нужно через поддерживаемыйUI проверить поля установленнойверсии и plan. Для точных365days имеется существующий apply-posthog-event-ttl.sh --dry-run --days365 и отдельный --status. Ни execute, ни rawDB PostHog mutations не выполнялись. ДоDDL оценить aggregateoldrows, все проекты/реплики/таблицы, backup+restore и последствия ужеистекшихстрок; затем отдельноеapproval конкретнойнеобратимойоперации. Не считать projectmonthsравным365days или установленныйминимум в GRAF доказательствомTTL.

## Метрики и проверка

Считать уникальных pseudonymoususers с текущимсогласием: первый наблюдаемый после согласия запуск -> подключенныйaccount -> первая запись -> readyresultview -> полезнаясессия. До согласия история не восстанавливается; download не означает установку, consentedactivation не totalactivation. Источник из существующего consentedhandoff/campaigncontext; unknown остаётсяunknown и не AI. Серверная accountmilestone может иметь unknownsource; известныйlaunchsource не затирать.

Отдельный ingestiontest нужен в изолированном PostHog/ClickHouse: syntheticonly UUIDfixtures, captureack, readback именноevents/uuid/distinctid, повтор после timeout/duplicate, пустыеIP/geoip и запретpayloadPII. Текущие fakeprovider/API/DB tests этого не доказывают. Productionfixtures не создавать.

Нужен реальный путь личного action под текущимнеизменённымnotice: API consentготов, но историческая ProductTelemetryGateViewModel не подключена к экрануacceptance. Не подменять это согласиемнастройками. После решенияlegal/runtime UIwiring должен быть отдельно доказан до выпуска; текстыполитик/лендингне трогать.

## Граница атрибуции подготовленного пакета

Явный маршрут отклоняет свободный текст и вложенные identity properties. Desktop не передаёт произвольные campaign/content/term и bridge ID: только закрытые категории source/medium, weak/unknown. Это не готовая сверка campaign bridge с серверным реестром и не доказательство organic activation. Неизвестное происхождение остаётся unknown. Полная связь источника требует отдельного подтверждения действующего реестра на стенде; не следует включать режим, обещая полную атрибуцию.

Отзыв личного согласия сохраняется при выключенном флаге, readiness blocker и смене версии. Повторное включение режима не превращает withdrawn в accepted.
