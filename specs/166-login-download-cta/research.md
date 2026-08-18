# Research: Контекстная ссылка на приложение на экране входа

## Decision 1: Использовать уже нормализованный `next` как контекст поверхности

**Decision**: считать вход embedded, если безопасный `next` начинается с
`/desktop/`; остальные безопасные значения считать web-входом.

**Rationale**:

- macOS-клиент уже восстанавливает сессию через `/login?next=/desktop/...`;
- `_safe_browser_next_path` сохраняет только same-origin абсолютные пути и
  отбрасывает внешний/двойной slash redirect;
- новый заголовок, cookie или client-side detection создали бы лишнюю
  trust-boundary и могли бы расходиться с фактическим маршрутом после входа;
- один guard в общем `render_login_page` покрывает первоначальный экран и все
  login error responses.

**Alternatives considered**:

- `X-GRAF-Client`: отклонено — текущая desktop policy намеренно не прикрепляет
  desktop headers к login/external navigation.
- отдельный `/desktop/login`: отклонено — дублирует route и auth flow.
- JavaScript по user-agent: отклонено — ненадёжно и не нужно для server-rendered
  поверхности.

## Decision 2: Вынести web CTA из карточки авторизации

**Decision**: web CTA является одной вторичной ссылкой на нижней левой области
auth viewport, вне `.auth-panel`; на узкой ширине он переходит в компактный
вертикальный layout без изменения назначения.

**Rationale**:

- primary task (email/provider login) остаётся визуальным центром;
- secondary product discovery link остаётся доступным до и после auth error;
- отдельная область сокращает конкуренцию с полем email и не создаёт второй
  action внутри карточки;
- видимый text link и focus state работают без hover и не требуют onboarding.

**Alternatives considered**:

- оставить CTA внутри карточки: отклонено — текущая компоновка недостаточно
  заметна и смешивает вход со скачиванием;
- показывать modal/banner: отклонено — увеличивает interruption и scope;
- скрывать CTA в web: отклонено — веб-пользователю нужен путь к приложению для
  записи.

## Decision 3: Сохранить все остальные download surfaces

**Decision**: изменять только `cabinet/auth/login.html`; referral landing,
public landing/download и authenticated sidebar остаются владельцами своих
CTA.

**Rationale**: пользовательская проблема относится к экрану login в приложении;
расширение guard на соседние auth или public pages создаст несовместимые
сценарии и лишний diff.
