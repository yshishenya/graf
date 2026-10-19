# Research: Безопасное восстановление авторизации и навигации

## Decision: Разделить устойчивую страницу и одноразовый переход

**Decision**: Сохранять как маршрут SwiftUI и native history только
повторно-открываемую GET-страницу. Любой POST, OAuth provider, callback и
вложенный auth action остаётся transient до прихода финальной стабильной
страницы.

**Rationale**: `DesktopCabinetWorkspaceView` создаёт декларативный GET из
`currentRoute`. Сохранение POST или OAuth URL превращает исходное действие в
новый GET и объясняет observed 501/429 и OAuth loop.

**Alternatives considered**:

- Добавить GET-обработчики на сервере — отклонено: меняет контракт и разрешает
  небезопасное воспроизведение действия.
- Внести список исключений только для VK/Yandex — отклонено: email и settings
  POST остаются уязвимыми.
- Удалить всю native history — отклонено: ломает ожидаемую навигацию встреч и
  настроек без необходимости.

## Decision: Узко определить безопасные auth documents

**Decision**: Корневые `/login` и `/sign-up` считаются стабильными auth
страницами; вложенные `/login/...` и `/sign-up/...` не являются документами
для истории или декларативной перезагрузки. Разрешение route policy сохраняется
для того, чтобы WebKit мог показать текущий шаг.

**Rationale**: Один route kind сегодня охватывает и корневую страницу, и
одноразовые start/verify URL. Отдельный predicate решает это без изменения
серверного allowlist и без расширения enum маршрутов ради одной политики.

**Alternatives considered**:

- Новый route kind для каждой формы — отклонено: дублирует URL semantics и
  расширяет exhaustive switches без дополнительной защиты.
- Считать все auth URL стабильными — отклонено: именно это создаёт повтор GET.

## Decision: Отложить очистку WebView history до стабильной смены сессии

**Decision**: POST не создаёт session boundary. Controller отмечает смену
сессии только после финальной stable auth/protected страницы; coordinator
сначала синхронизирует route и request identity, затем очищает history/remount.

**Rationale**: Текущий `historyFencePending` пересоздаёт WebView в середине
email form/OAuth. При логине, logout или 401 прежняя history всё равно должна
быть уничтожена, но только когда есть безопасная целевая страница.

**Alternatives considered**:

- Оставить fence на каждом POST — отклонено: ломает незавершённый вход и формы.
- Никогда не очищать WebView history — отклонено: может открыть protected page
прошлой сессии.

## Decision: Явно различать sign-in OAuth и provider-link OAuth

**Decision**: Использовать маленькое состояние continuation (`none`, primary
sign-in, authenticated provider link). Оно разрешает внешний provider только
после одобренного старта и определяет, должна ли provider/callback страница
перевести shell в auth-required state.

**Rationale**: `/desktop/settings/provider-links/{provider}/start` — это
authenticаted POST, который ведёт на внешний OAuth, но не создаёт новую сессию
GRAF. Текущий boolean допускает только login-origin flow и смешивает эти
сценарии.

**Alternatives considered**:

- Разрешать любой внешний URL из Settings — отклонено: ослабляет origin boundary.
- Использовать два независимых boolean — отклонено: допускает противоречивое
состояние; enum короче и закрывает невозможные комбинации.

## Decision: Проверять порядок настоящим WKWebView в существующем наборе

**Decision**: Переиспользовать синтетический loopback HTTP fixture текущего
`DesktopCabinetWorkspaceTests.swift`; pure policy assertions дополняют, но не
заменяют проверку controller/coordinator и SwiftUI `.id`.

**Rationale**: На базовом master диагностическая проба с настоящими state/route
bindings дала GET 200 PASS и POST 200 FAIL именно по `sessionBoundaryID`.
Старое утверждение об отсутствии WK fixture больше не актуально.

**Alternatives considered**: Новый тестовый framework или перенос архивной
реализации целиком не нужны. Внешние провайдеры и реальная сессия для этой
причинной проверки не требуются.

## Текущие доказательства и нерешённое наблюдение

База: `c6c5441c930b8c1ecffed6de9b80773aa0e757e5`.
Внешний реестр: `/Users/yshishenya/Documents/Codex/2026-10-16/graf-issue-by-issue/`.
`F136-boundary-probe-result-20261017.json` и
`F136-boundary-probe-tests.swift` фиксируют 1 PASS / 1 ожидаемый FAIL;
source SHA256 `2bff1dc68c99c888a13fcb7abab7a28f7267a38e479000526ad16a665a8142f1`.
Это исходное воспроизведение, а не положительная приёмка исправления.

Зависание синтетического 303 отмечено в отдельном redirect-observation log.
Причина не доказана; оно не входит в доказательство POST→session boundary.
Не ослаблять navigation identity/отклонение устаревших callbacks ради обхода.

## Decision: Подтверждать перенаправление по идентичности WKNavigation

**Decision**: Ожидающий navigation action временно блокирует terminal callback
предыдущего документа. Новый provisional start заменяет identity; native
`didReceiveServerRedirectForProvisionalNavigation` подтверждает продолжение
того же активного WKNavigation. Не определять redirect по одному HTTP-методу
или совпадению URL и не восстанавливать уже отклонённый старый identity.

**Rationale**: Настоящий POST→303 fixture подтвердил: WebKit передаёт новый
GET как `.formSubmitted` с тем же WKNavigation. Старый `retirePreviousNavigation`
ошибочно инвалидировал именно его; конечный didFinish отвергался и оставлял
loading. Диагностический журнал `F136-redirect-identity-diagnostic-20261017.log`
содержит только синтетические типы/методы и временные object identities;
временные print полностью удалены. До изменения 1 FAIL / 0 unexpected;
после — новый redirect case и существующий same-URL stale-finish case PASS.

**Alternatives considered**: Не ослаблять проверки всех terminal callbacks,
не делать исключение только для GET/POST или совпадающего URL, не повторять
сетевой запрос и не добавлять private WebKit API.

Отмена текущего завершённого перехода не оставляет loading: coordinator
применяет существующее безопасное состояние malformedResponse, сохраняя
исходный WebView и не повторяя форму. Это не меняет статическую классификацию
ожидаемых отмен в других местах приложения.
