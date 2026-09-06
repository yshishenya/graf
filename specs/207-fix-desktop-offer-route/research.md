# Research: Safe Desktop Offer Route

## Decision 1: Browser-owned legal route

**Decision**: Точный same-origin путь `/offer` классифицируется как безопасный browser-owned документ и открывается во внешнем браузере.

**Rationale**: Оферта является публичным legal-документом вне embedded cabinet. Пользователь должен прочитать её до согласия, а desktop checkout должен оставаться открытым.

**Alternatives considered**:

- Разрешить оферту внутри WebView — отклонено: это смешивает public browser page с embedded cabinet и не даёт преимуществ для checkout.
- Переписать server link — отклонено: installed desktop client всё равно применяет собственную allowlist policy к переходу.
- Разрешить все public routes — отклонено: нарушает fail-closed boundary.

## Decision 2: Reuse existing sanitization

**Decision**: Переиспользовать `DesktopCabinetRoutePolicy.sanitizedExternalURL(for:)`, сохраняя только scheme, host, port и канонический path.

**Rationale**: Механизм уже используется для browser-owned маршрутов и не переносит query, fragment, user info или payment data.

**Alternatives considered**:

- Новый handoff endpoint/token — отклонено: публичная оферта не требует auth и новая state machine не нужна.
- Передавать исходный URL целиком — отклонено: query и fragment могут содержать ненужные данные.

## Decision 3: Minimal shared-policy patch

**Decision**: Добавить один точный case в существующую policy и focused regression checks.

**Rationale**: Корневая причина находится в общей классификации маршрута; patch server template или отдельного click handler оставит sibling callers уязвимыми к тому же несоответствию.

**Alternatives considered**:

- Новая legal-route abstraction — отклонено: один канонический route не оправдывает новый слой.
