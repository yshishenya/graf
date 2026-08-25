# Research: Включение Яндекс Календаря

## Decision: переиспользовать существующий CalDAV adapter

`apps/server/src/twobrain_rec_server/calendar/caldav.py` уже выполняет read-only
PROPFIND для каталога и REPORT для событий, нормализует iCalendar и ограничивает
redirect тем же public origin. `caldav_yandex` уже имеет preset URL
`https://caldav.yandex.ru/` и auth mode `app_password`.

**Rationale**: новый SDK или provider framework не добавит ценности и расширит
credential/egress surface.

**Alternatives considered**: отдельный Yandex API/OAuth adapter отклонён — он не
нужен для календарного чтения, а утверждённый текущий путь использует пароль
приложения и CalDAV.

## Decision: включать только после real E2E receipt

Текущий capability matrix намеренно держит все семьи в `Скоро`, пока нет
полного real browser/embedded matrix. Synthetic HTTP и PostgreSQL tests доказывают
контракт, но не доказывают реальный аккаунт, каталог, sync и disconnect.

**Rationale**: production UI не должен обещать работающий provider на основании
только mock/fixture evidence.

**Alternatives considered**: открыть UI сразу после unit tests отклонено;
отдельная глобальная feature platform отклонена как избыточная для одного
провайдера.

## Decision: credential остаётся серверным

Пароль приложения принимается только на серверном connect flow, запечатывается
существующим Fernet envelope и используется worker-ом. macOS получает только
серверный read model.

**Rationale**: сохраняются текущие privacy, RLS, deletion и no-secret gates.

## Decision: rollout и release разделены

Проверка тестового аккаунта и включение provider capability — отдельная фаза от
production release/deploy. До explicit approval production не меняется.

**Rationale**: real provider evidence, exact-SHA CI и live production smoke —
разные gates.

## Decision: пятиминутная сверка использует существующий maintenance worker

Периодическая проверка не создаёт внешний scheduler: текущий maintenance loop
проверяет активные `caldav_yandex`-источники с выбранными календарями и ставит
их в очередь после истечения пяти минут с последнего запуска. Подключение,
сохранение выбора и ручная кнопка используют тот же provider sync runner; для
ручной кнопки runner выполняется до возврата ответа.

**Rationale**: сохраняются общий tenant/RLS lifecycle, безопасные retry/error
states и единственная точка provider I/O. Google и другие провайдеры не
попадают в Yandex-only расписание.

## Открытые внешние зависимости

- Выделенный тестовый аккаунт Яндекс Календаря с паролем приложения.
- Аутентифицированный browser и embedded macOS runtime для сценариев connect,
  catalog, selection, sync, reconnect и disconnect.
- Доступный disposable PostgreSQL для integration closeout.

Ни один секрет или содержимое встреч не записывается в репозиторий или чат.
