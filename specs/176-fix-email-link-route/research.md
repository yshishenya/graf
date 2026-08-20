# Research: Стабильное подключение email в приложении

## Decision 1: исправлять ownership навигации в macOS shell

Production-последовательность подтверждает: POST успешно отправляет код, после
чего shell открывает тот же URL как GET и получает 405. Серверный POST-only
контракт корректен; добавлять GET fallback означало бы скрыть ошибку клиента и
размыть CSRF/idempotency границу.

## Decision 2: переиспользовать существующий request-identity predicate

`EmbeddedCabinetWebView` уже отделяет transient OAuth/email form navigation
от SwiftUI-owned documents. Расширение этого владельца меньше и безопаснее
нового router, state store или endpoint-specific workaround в UI.

## Decision 3: учитывать метод, direct-response URL и активную загрузку

До завершения navigation доступен исходный `URLRequest`, поэтому любой non-GET
не должен обновлять воспроизводимый route. После `didFinish` WebKit отдаёт
только URL; direct-response email start/verify endpoints остаются в существующем
transient allowlist, чтобы future SwiftUI rebuild также не превратил их в GET.
Их POST-документы остаются в unsafe history ledger и не требуют пересоздания
WebView. Когда WebKit уже загружает тот же active/pending URL, `updateNSView` не
начинает дубликат. Отличающийся внешний route не блокируется и может заменить
текущую загрузку; завершившийся документ остаётся видимым.

## Decision 4: сохранять полезные email-link error documents

Start/verify endpoints намеренно возвращают локализованный HTML при invalid,
expired, replayed, rate-limited и delivery-unavailable состояниях. Узкий
response-policy allowlist для этих двух embedded form endpoints сохраняет
полезный recovery context; остальные settings failures продолжают проходить
существующую классификацию.

## Rejected alternatives

- GET fallback на POST-only endpoint: маскирует root cause и создаёт неверный
  контракт для изменяющего действия.
- Хранить email/code/state в route: нарушает privacy и replay boundaries.
- Новый navigation state machine: не нужен; существующих request identity,
  loading state и safe/unsafe history ledgers достаточно.
- Менять delivery, callback state или account merge: production-факты не
  указывают на сбой этих компонентов.
