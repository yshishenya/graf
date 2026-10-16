# Независимый review реализации минимальной воронки

Дата: 2026-10-03. Область: dirty implementation 096-explicit-funnel-remediation; reviewer header_review. Проверены explicit_funnel, authenticated API, PostHog wrapper, nullable migration 0102, desktop refresh/reset и receipt, имеющиеся новые server/Swift tests. Код, требования, GitHub и production reviewer не изменял.

## Вердикт

Повторный review: оба первоначальных P1 устранены в текущем рабочем дереве. Новых P0/P1 в просмотренном diff не выявлено. Исторические находки ниже сохранены для связи с исправлениями. Production режим остается default-off; реальных provider/ClickHouse запросов не выполнялось.

## P1: allowlist ключей допускает произвольный контент и вложенную подмену identity

validate_milestone передает properties в существующий build_activation_event. Он проверяет имена полей и общие forbidden patterns, но не закрытые значения полей минимального события. COMMON_FIELDS разрешает stable_pseudonymous_user_id внутри properties; этот claim не связан с principal. Верхний identity защищен, вложенный — нет.

Локальная синтетическая проверка без сети/БД/provider показала:

- first_value_session_completed с useful_result_type, содержащим свободную синтетическую фразу о непубличном проекте, принят неизменно;
- properties.stable_pseudonymous_user_id с синтетическим raw_account_12345 принят неизменно и отличается от server-owned identity;
- обе формы проходят и assert_no_forbidden_fields, и assert_no_security_credential_fields, вызываемые PostHog wrapper.

Последствие: минимальная отправка способна сохранять content/raw identifier под разрешенным именем поля и давать противоречивую identity. Это не только теоретическая слабость regex: путь validate → wrapper не отбрасывает эти значения. Настоящие PII или содержание встреч для воспроизведения не использовались.

Исправление: отдельный минимальный event-specific values schema для категорий/флагов/версий/числовых buckets и ограниченных campaign значений; reserved identity properties либо отклонять, либо формировать только сервером. Добавить тесты вложенного чужого/raw ID и произвольной фразы в useful_result_type/другом разрешенном поле; обе формы должны давать 0 provider calls. Legacy broad contract менять не требуется.

## P1: отзыв согласия зависит от готовности включения сбора

change_consent для accepted=False применяет те же configuration_allowed/current-copy условия, что и для принятия. Проверено синтетически: при сохраненном accepted consent выключение explicit_funnel_enabled делает withdrawal недоступным. Аналогично legal/privacy readiness или copy-version mismatch закрывают путь записи отзыва.

Последствие: попытка пользователя отозвать существующее согласие получает отказ, accepted запись остается; возврат прежней конфигурации/версии вновь разрешает сбор без нового подтверждения, несмотря на попытку отзыва. Отключение отправки сейчас не заменяет сохраненный withdrawal. Это вопрос состояния разрешения, а не публикации нового disclosure.

Исправление: authenticated/CSRF-protected withdrawal должен сохраняться независимо от provider readiness/старой версии; acceptance остается за текущими строгими gates. Возвращать закрытый context и не делать provider calls. Проверить accepted → readiness off → withdrawal → readiness on и stale-copy withdrawal: сбор остается закрытым.

## Проверенные защитные свойства

- Principal/top-level pseudonym связан сервером; явный чужой top-level ID отклоняется.
- Tenant context и WHERE user_id/organization/status сохраняют user boundary. Consent и events блокируют ту же user row, что сериализует события и отзыв; при network call lock удерживается, поэтому latency следует учитывать в release proof.
- Cookie mutations используют существующий require_web_csrf; context GET выдает токен только для cookie session. Для bearer/native используется текущий transport contract.
- Provider blocked/error не записывает durable milestone. Retry UUID стабилен; ambiguous acceptance/DB failure может повторить UUID, а фактическая provider дедупликация еще требует synthetic ingestion proof.
- Account milestone server-owned. При успешной account delivery и отказе второй вехи DB receipt откатывается, поэтому account повторится тем же UUID — не считать это доказанным exactly-once без PostHog readback.
- Desktop contextGeneration защищает от позднего context refresh после invalidation; server identity повторно проверяется при событии. Нынешние tests не воспроизводят suspended refresh/send при auth switch и cookie-session CSRF: нужны targeted regression checks, хотя подтвержденной обходной отправки в просмотренном коде не выявлено.
- Migration nullable/additive, без backfill; retention/purge не применяются. Drop-column downgrade уничтожил бы metadata consent/receipts, поэтому rollback/migration rehearsal отдельно обязателен.

## Что не доказано

23 server/DB и 27 Swift PASS сообщены владельцем; reviewer не подменяет ими новые privacy cases выше. Fake-provider acceptance не доказывает ClickHouse ingestion, retention 365, effective no-IP enrichment, production backup/restore или management access. $geoip_disable/$ip:null видны в коде, но их фактическая интерпретация установленным PostHog требует isolated ingestion/readback. Реальный user-action consent UI путь и notices mapping остаются operational blockers. Нет разрешения production enablement/новых keys/grants/purge.

## Повторный review исправлений P1

Закрытая values schema теперь отклоняет свободный полезный-result текст, вложенные identity claims, raw identifiers, campaign names/content/term и неизвестные значения источников. Существующий event-specific key allowlist применяется поверх закрытой схемы. Native explicit route удаляет bridge ID/free campaign fields и оставляет только конечные client-reported категории weak/unknown; реальная registry linkage этим не заявляется.

Независимо повторены прежние локальные синтетические reproductions: обе запрещенные properties теперь дают ValueError; withdrawal при disabled mode сохраняется и после возврата исходной конфигурации context остается withdrawn. Acceptance по-прежнему требует текущую готовую версию. Просмотрены новые unit cases и API disabled-withdrawal regression; actual native call-site значения version/platform/install channel/duration/capture/result согласуются с новым каталогом.

Новых P0/P1 не выявлено. Runtime ingestion, noIP на установленном провайдере, retention, user-action UI, CSRF-cookie/race regression и operational proofs по-прежнему не переаттестованы этим review. Согласие не делает клиентские milestones или coarse acquisition серверно доказанными фактами; такую оговорку сохранить в dashboards. Reviewer изменил только этот отчет, без кода/требований/remote.
