# Research: Надёжный переход локальной записи в кабинет

## UTF-8 bridge

**Decision**: Декодировать base64 в байты и применять браузерный `TextDecoder` перед `JSON.parse`.

**Rationale**: `atob` возвращает binary string, поэтому прямой `JSON.parse(atob(...))` повреждает UTF-8 кириллицу.

**Alternatives considered**: Экранировать Unicode вручную — больше кода и повторяет стандартный декодер; передавать JSON literal — сложнее безопасно встроить в script.

## Local row action and handoff

**Decision**: Локальная строка имеет отдельное native `open` действие; server row не получает local ID. Локальная строка скрывается только когда upload завершён и соответствующая server row уже присутствует.

**Rationale**: Локальный файл принадлежит native custody, server detail — авторизованному web route. DOM grafting смешивает две идентичности и оставляет строку без основного действия.

**Alternatives considered**: Синтетический web URL для локального файла отвергнут из-за раскрытия пути и route-policy boundary; сохранение двух строк после upload создаёт дубль.

## Duration and failure category

**Decision**: Верхнеуровневую длительность v5 брать из фактического media/playback файла с wall-clock fallback. Неuploadable текущий v5 package классифицировать как `local_resource` и переносить `captureFailureCode`; при refresh исправлять старую `schema_incompatibility`.

**Rationale**: Wall-clock интервал не равен длине безопасно сохранённого prefix. Схема валидна; проблема локального capture/resource класса.

**Alternatives considered**: Менять только подпись UI отвергнуто — stale queue semantics и неверная диагностика останутся.

## AEC input boundary

**Decision**: В `RecordingEchoProcessor` после проверки размера и finiteness ограничивать конечные входы до −1…1; ошибки библиотеки остаются терминальными. Timeline сохраняет исходную clipping metric.

**Rationale**: Hardware/capture conversion может дать конечный overshoot. Это качество/клиппинг, не нарушение целостности кадра; WebRTC float API ожидает нормализованный диапазон.

**Alternatives considered**: Игнорировать overshoot отвергнуто из-за воспроизводимого свежего сбоя; clamp во всех source adapters дублировал бы логику и пропустил sibling callers.

## Existing data cleanup

**Decision**: Использовать существующий queue deletion service для четырёх точных item IDs/directories после проверки allowlist и сохранности успешной встречи.

**Rationale**: Сервис валидирует корень, удаляет package и пишет terminal state атомарно; ручное редактирование queue JSON недопустимо.

**Alternatives considered**: Простое перемещение каталогов без queue transition оставит stale строки; массовая очистка слишком широка.
