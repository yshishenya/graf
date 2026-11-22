# Contract: Desktop support incident report v2

## Request

`POST /api/v1/desktop/support-incidents`

- Authenticated embedded-cabinet session and existing CSRF/idempotency rules
  remain required.
- New clients send `schema_version: desktop-support-incident.v2` and
  `redaction_state: metadata_only`.
- Server accepts `desktop-support-incident.v1` during migration.
- Unknown fields containing credentials, tokens, cookies, signed URLs, raw
  audio, transcript/content, email/name or paths are rejected before mutation;
  unknown harmless fields are not trusted and are omitted/redacted.
- All IDs crossing the report boundary are opaque fingerprints. The server may
  store scoped identifiers internally but never puts them in the Issue body.

## Response

The existing `SupportIncidentResponse` remains compatible:

```json
{
  "incident_id": "CUST-...",
  "incident_status": "synced|pending_sync",
  "github_issue_number": 123,
  "github_issue_url": "https://github.com/...",
  "dedupe_status": "created|updated",
  "affected_count": 1,
  "copy_fallback_available": true,
  "user_message": "..."
}
```

The URL/number are returned only through the existing authenticated response;
the clipboard fallback remains useful when they are absent.

## Compatibility and bounds

- Missing v2 fields are represented as `unknown` in the server report.
- `retry_history` and `timeline` are limited to five events each; affected
  fingerprints to five; serialized report to 256 KiB.
- The server computes authoritative CUST/fingerprints and does not trust the
  client correlation values for tenant scoping or dedupe.

## Дополнение для T083 (Windows): проект, ещё не действует

Цель — отправлять безопасную сводку с обеих платформ по одному сценарию.
Кабинет, CSRF, существующие маршруты создания и синхронизации и структура
ответа сохраняются. Windows получает CUST и может скопировать сводку даже
при недоступной синхронизации; существующие Mac v1/v2 продолжают работать.

**Предлагаемая версия отчёта.** Ввести `desktop-support-incident.v3`.
Сервер явно различает `platform: windows` и `platform: macos` и принимает
только соответствующее поле версии ОС с существующими ограничениями на
безопасные строки. Обязательные сочетания платформы и идентификатора
приложения проверяются по разрешённому списку. Платформа из отчёта служит
для диагностики; права определяет действующая сессия. Windows получает
`feature:114` и `area:windows`. Для v1/v2 остаётся `area:macos`;
отсутствие метки Windows не должно мешать синхронизации Mac. Старый
сервер явно отклоняет v3 до записи в базу и обращения в GitHub. Клиент
показывает возможность скопировать сводку и не пересылает Windows как v2.

**Два разных повтора.** Повтор создания с тем же ключом и отчётом возвращает
текущий результат для того же CUST, не увеличивает число затронутых
записей и не вызывает GitHub. Ключ проверяется в границе исходного
пространства, автора и устройства; другая сессия того же автора может
повторить действие только после обычной проверки доступа. Ключ с другим
отчётом в той же области даёт конфликт. Чужой ключ сам по себе не раскрывает
чужой CUST, метаданные или наличие обращения; чужой sync даёт 404.
Отдельный ручной sync не принимает новое тело отчёта и работает с ранее
созданным CUST. Синхронизация и возвращение позднего результата не дают
доступа отозванной сессии.

**Потерянный ответ GitHub.** До вызова создания GRAF надёжно фиксирует
попытку под тем же CUST. Только одна попытка может начать создание.
Если вызов мог завершиться созданием, а подтверждения нет, состояние
остаётся `pending_sync`. При ручной синхронизации сервер сверяет его по
точному маркеру CUST, доверенному автору и разрешённому закрытому репозиторию.
Один подтверждённый результат привязывается к тому же CUST. Отсутствие
результата, несколько совпадений, ошибка сверки или её задержка не дают
разрешения на повторный POST. Это правило действует и после перезапуска.
Повторное создание допустимо только если предыдущий вызов гарантированно
не мог создать Issue. Для старого `pending_sync` с неизвестным исходом
действует та же сверка; известные синхронизированные обращения сохраняют
ссылку. Клиент оставляет номер и копирование, пока сервер не подтвердит
синхронизацию.

**Критерии проверки перед подключением Windows.** В изолированном
серверном тесте с подменой GitHub: v1/v2 Mac дают прежние результаты;
Windows v3 получает правильные поля и метки; старый сервер отвергает v3,
а обновлённый отвергает запрещённое содержимое; отсутствие метки Windows
изолировано от Mac. Для обоих клиентов проверить повтор после перезапуска,
изменённое тело под прежним ключом, другого автора и устройство, гонку двух
запросов, потерю ответа до и после создания, задержку сверки и точное
подтверждение единственного Issue. Считать вызовы создания отдельно
от количества CUST. Для гонки ручного sync использовать две отдельные
транзакции с подтверждённым пересечением: первая получает успешный ответ
создания, вторая ждёт и затем видит ту же ссылку либо возвращает тот же
CUST в состоянии ожидания. Ровно один вызов создания; последующий
одиночный sync возвращает единственную сохранённую ссылку. Сценарий
потерянного ответа проверяется отдельно: ожидание блокировки само по
себе не подтверждает, что внешний Issue отсутствует.
Проверку маршрутов с действующей сессией и CSRF, сменой аккаунта и
отзывом доступа выполнить отдельно от модульных тестов.
