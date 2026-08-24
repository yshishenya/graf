# Contract: processing status и user recovery UI

**Feature**: `195-processing-recovery`
**Статус**: proposed additive projection; не является готовой OpenAPI-схемой

## Цель

Пользователь должен понимать результат без знания MediaScribe. Projection
строится из PostgreSQL state, а не напрямую из provider response.

## Suggested projection

Названия полей — design-level; точные Pydantic names выбираются при реализации.

```json
{
  "state": "waiting_retry",
  "stage": "result",
  "reason_code": "provider_unavailable",
  "retry_class": "retryable",
  "next_attempt_at": "2026-08-23T10:03:00Z",
  "server_time": "2026-08-23T10:02:00Z",
  "manual_action": "check_now",
  "attempt_in_flight": false,
  "artifacts": {
    "transcript": {"state": "available", "visible": true},
    "diarization": {"state": "available", "visible": true},
    "summary": {"state": "running", "visible": false},
    "playback": {"state": "available", "visible": true}
  }
}
```

Обязательные поля:

- `state`, `stage` — GRAF lifecycle, не raw provider enum;
- `retry_class` — `none`, `retryable`, `unknown_outcome`, `terminal`;
- `next_attempt_at` — nullable absolute timestamp;
- `server_time` — для корректного countdown после refresh/background;
- `manual_action` — `none`, `check_now`, `new_attempt`, `contact_support`;
- `attempt_in_flight` — защита от двойного действия;
- artifact states и `visible` — независимые flags с server enforcement.

Provider job id, idempotency key, signed URLs и raw `detail` в projection
отсутствуют.

## Visibility invariant

Обычная вкладка «Расшифровка» получает `available=true` и сегменты только если
выполнено всё:

```text
same media_revision_id
same processing_attempt_id
transcript artifact = available
diarization artifact = available
diarization validated and non-empty
deletion epoch is current
viewer has meeting access
```

До этого момента:

- сегменты, импортированные раньше, остаются server-side intermediate data;
- UI показывает «Спикеры ещё определяются. Расшифровка появится после
  завершения диаризации»;
- нет обычного search/export/transcript download;
- summary/playback statuses могут отображаться отдельно, но не раскрывают
  transcript.

Если transcript недоступен по `no_recognizable_speech`, UI показывает
«Речь не распознана» и не выдаёт пустой успешный transcript.

## Summary independence

| Transcript + diarization | Summary | UI |
|---|---|---|
| ready | running/queued | «Расшифровка» доступна; «Итоги готовятся» |
| ready | failed | transcript доступен; ошибка и action только у итогов |
| ready | not requested/unavailable | transcript доступен; summary обозначен как недоступный |
| not ready | any | transcript скрыт; processing state объясняет следующий шаг |

GRAF-owned summary остаётся основной пользовательской summary surface. Provider
summary может быть отдельным internal artifact и не заменяет этот pipeline без
отдельного решения качества/доверия.

## Retry state and copy

### Temporary retry

Показывать только когда server state `retry_class=retryable` и операция безопасна:

- status label: «Обработка временно приостановлена»;
- explanation: «Запись сохранена. GRAF попробует проверить её автоматически.»;
- exact timestamp: только если `next_attempt_at` рассчитан из валидного hint;
- countdown: «Следующая проверка через …»;
- primary button: «Проверить обработку»;
- `aria-live=polite` только для переходов и крупных изменений, не каждую секунду.

Если hint отсутствует/невалиден, не обещать дату: «Попробуйте сейчас или
обновите страницу позже». Кнопка остаётся доступной, если safe same-job check
возможен.

### Manual check

После POST/Update:

1. server атомарно проверяет active attempt, deletion epoch и current schedule;
2. если операция уже in-flight, возвращает актуальный state без второй job;
3. если timer pending, увеличивает schedule generation и очищает timer;
4. workflow выполняет одну проверку того же provider job/key;
5. UI сразу сбрасывает countdown, блокирует кнопку и показывает
   «Проверяем сейчас»;
6. ответ либо делает artifact available, либо создаёт новый countdown/terminal
   action.

Double click, две вкладки, refresh после click и проснувшийся старый timer
должны приводить к одному результату.

### Unknown upload outcome

UI не предлагает «загрузить ещё раз» при `unknown_outcome`. Copy:

> Не удалось подтвердить отправку, поэтому GRAF проверяет исходную попытку и
> не создаёт дубликат.

Action — «Проверить сейчас», если есть source revision и same-key evidence;
иначе — «Нужна помощь»/support handoff с safe request id.

### Terminal failure

Не показывать countdown. Разделять:

- повреждённый/неподдерживаемый файл — исправить источник и начать новую
  обработку явно;
- provider processing failure — support/new attempt по policy;
- auth/configuration failure — пользователь не должен бессмысленно нажимать
  retry; action для оператора.

Уже доступные artifacts остаются доступными и не скрываются из-за failure
другого artifact.

## List and detail parity

List, web detail и embedded desktop detail получают одинаковые server fields:

- artifact availability;
- retry class and safe reason;
- next attempt server timestamp;
- manual action;
- attempt in flight.

Desktop может иметь native navigation/offline behavior, но не имеет отдельного
retry state и не вызывает MediaScribe напрямую.

## Accessibility and localization

- button имеет понятную accessible name и disabled/busy state;
- countdown не является единственным способом узнать состояние;
- переходы состояния объявляются через polite live region;
- focus не теряется после HTMX/fragment refresh;
- keyboard, screen reader, reduced motion, forced colors и background tab
  обязательны для acceptance;
- copy keys локализуемые, provider code — только в details/support view;
- server timestamp + client `Date.now()` offset не должны давать negative или
  «скачущий» countdown.
