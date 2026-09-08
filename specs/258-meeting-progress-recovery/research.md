# Исследование и решения

Дата: 2026-09-08. Исходный SHA: e81b412dff920cc29ed37de60be13dd8fc4d1c43.

## Проверенные причины

- `cabinet/egress.py:_latest_accepted_media_revision` возвращает None при пустом default summary slot. Оба callers — playback state и stored audio artifacts — скрывают готовый звук. Опубликованный результат должен сохранять закреплённую media revision.
- `processing/status.py` учитывает опубликованный slot, но не queued/generating/blocked attempt. Старое not_requested останавливает polling. Partial summary не признаётся готовым при fragment refresh.
- `cabinet.js:reloadAfterSummaryChange` делает replaceState, затем reload; WKWebView разрешает reload только зарегистрированного safe history URL. Исторический отказ WebKit не записан отдельно: механизм подтверждён кодом/моделированием, не выдан за наблюдавшийся лог.
- Polling candidate/manual refresh прекращается по 40 попыткам/5 минутам или первому сбою запроса; длительность не является terminal state.
- `DesktopUploadQueueService.needsProcessingFollowUp` завершает processed; sync не передаёт summary state. Переиспользовать существующий опрос, не второй pipeline.
- Native presenter имеет reminders/incidents/test, но не start/recap; реальные foreground events подавлены. Incident grouping берёт только primaryItem, retentionDeadline используется как срок уведомления, не все нужные события вызывают refresh.
- Media worker делает SELECT processing_workflows без grant; timer fallback спасает обработку. Исправление не должно давать broad DML/admin.

## Krisp: наблюдаемое и ненаблюдаемое

В установленном интерфейсе проверены Notifications: upcoming meetings, meeting recap, on/off indicator; AI Note Taker: auto-start, auto-open page, auto-summary, auto-title. На искусственной существующей встрече — отдельные AI Notes/My Notes/Transcript и player. Настройки не менялись, генерация не запускалась. Доставка и тайминг реальных баннеров не измерены. Частные скриншоты/встречи в git не копируются. Код, ресурсы, закрытые API не извлекались.

Решение: короткий сигнал плюс постоянное управление, независимый player, автоматические заметки; отклонено обещание ненаблюдавшихся таймингов. F255 menu сохраняется. Тексты ошибок правдивые для GRAF.

## Минимальное исправление

1. Развязать пустой slot и playback; не подставлять другую revision после невалидного опубликованного pointer.
2. Общая безопасная summary projection по slot/source/attempt; ready только опубликованное содержимое, dependency waiting не terminal, прежний результат доступен.
3. Автоматические фрагменты сохраняют player/focus/title; безопасный обычный GET вместо незарегистрированной history mutation, когда навигация необходима. WKWebView guards не ослабляются.
4. Продолжать GET polling с backoff/visibility/online, connected/generation; таймер не вызывает POST генерацию.
5. Native readiness только metadata sync своих записей и подтверждённая auth epoch. Нейтральный recap, claims от дублей/старых событий; веб-inbox не импортируется.
6. Инциденты по каждой записи до компактной группировки; freshness не retention, recovery завершает occurrence, retry не новое событие.
7. Минимальный metadata lookup workflow с column SELECT grants и RLS от настоящей media role; не скрывать ошибку вместо исправления.

## Baseline

68 existing processing/summary/playback contract tests PASS, два предупреждения. Найденные сочетания не покрыты: baseline не доказательство исправлений. F249 дополнительно исследован отдельным read-only research agent по speckit-plan.
