# Research: Надёжная навигация кабинета

## Decision 1: выбирать ближайший отличный history item

- **Decision**: Для back и forward фильтровать историю по существующей route
  policy и safe/unsafe URL ledger, дополнительно исключая элементы с URL,
  равным текущему. Выбранный `WKBackForwardListItem` открывать через
  `webView.go(to:)`.
- **Rationale**: Текущий код выбирает back item через
  `backList.reversed().first`, но не исключает дубликат текущего URL. Для
  forward он проверяет только `forwardItem`, а затем вызывает `goForward()`.
  При дубликатах это либо оставляет пользователя на том же экране, либо
  делает кнопку «Вперёд» недоступной, хотя дальше есть безопасная запись.
  `go(to:)` сохраняет идентичность нужного элемента и позволяет пропустить
  несколько дубликатов.
- **Alternatives considered**:
  - Удалить кнопку «Вперёд»: отклонено, поскольку браузерная история уже
    существует и сценарий отмены возврата полезен.
  - Вызывать сырой `goBack()`/`goForward()`: отклонено, поскольку это обходит
    существующие session/auth/route ограничения.
  - Считать любой URL в WebKit history безопасным: отклонено, поскольку
    ledger и route policy защищают auth, POST, external и artifact routes.

## Decision 2: не менять серверные маршруты и модель состояния

- **Decision**: Оставить текущие `canGoBack`, `canGoForward`, `canReload`,
  `canGoHome`, `isLoading` и существующую `DesktopCabinetRoutePolicy`.
- **Rationale**: Дефект находится в выборе history item и синхронизации
  состояния, а не в URL-контрактах кабинета. Это минимальный общий фикс для
  календарей, настроек, встреч и billing.

## Decision 3: проверять UI на установленном GRAF и через XCTest

- **Decision**: Использовать установленный GRAF для smoke-пути и accessibility
  snapshot, а SwiftPM XCTest — для детерминированных policy/selection правил.
- **Rationale**: Unit-тесты не доказывают, что titlebar-кнопки действительно
  отображают опубликованное состояние, а ручной smoke не покрывает все
  комбинации небезопасной истории. Вместе эти проверки закрывают оба риска.
