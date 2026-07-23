# UX And Information Architecture: Calm Recording Workflow

## Decision

Feature 121 MUST feel like one short route, not a control center:

```text
Начать запись → видеть, что запись идёт → остановить
→ открыть итоги → при необходимости поделиться
```

The service may keep detailed capture, custody, processing, revision, access,
export, and deletion states internally. The interface exposes only the current
human state, whether the recording is safe, and the one next action that needs
the user.

The three initial visual concepts are rejected as too dense. In particular, a
permanent lifecycle stepper, a permanent inspector, and simultaneous transcript,
summary, template, and sharing controls visualize the backend instead of the
user's task.

## Simplicity Contract

1. One primary action per state.
2. Healthy defaults stay quiet; details appear on request or when something is
   wrong.
3. Normal background work does not ask the user to manage retries or stages.
4. Alerts interrupt only for an actionable safety or irreversible decision.
5. A meeting page shows useful meeting content, not pipeline administration.
6. Safe defaults eliminate choices: system audio is part of normal capture,
   summary format is `Авто`, sharing is invite-only + summary-only + view-only.
7. Advanced policy never appears as disabled clutter. It remains absent until
   the workspace policy actually enables it.
8. The same interface serves first-time, returning, and advanced users. Speed
   comes from remembered defaults, menu bar control, keyboard shortcuts, and
   multi-address paste, not a separate expert mode.

These decisions follow the current Apple guidance to integrate ordinary status
near its object and reserve alerts for important actionable interruption, keep
menus short and contextual, use a prominent button only for the most likely
action, and use direct language. They also follow W3C guidance for clear page
structure, concise status messages, visible focus, and predictable modal focus.

References:

- Apple HIG: [Feedback](https://developer.apple.com/design/human-interface-guidelines/feedback), [Alerts](https://developer.apple.com/design/human-interface-guidelines/alerts), [Buttons](https://developer.apple.com/design/human-interface-guidelines/buttons), [Menus](https://developer.apple.com/design/human-interface-guidelines/menus)
- W3C WAI: [Clear page structure](https://www.w3.org/WAI/WCAG2/supplemental/patterns/o2p03-page-structure/), [Clear content](https://www.w3.org/WAI/WCAG2/supplemental/objectives/o3-clear-content/), [Modal dialog](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/), [Status messages](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html)
- GOV.UK Design System: [Details](https://design-system.service.gov.uk/components/details/) for optional information revealed only when needed
- Krisp behavior benchmark: [Recording](https://help.krisp.ai/hc/en-us/articles/11734566901788-Recording-your-meetings-with-Krisp), [Meeting Notes Templates](https://help.krisp.ai/hc/en-us/articles/26708055686044-Meeting-Notes-Templates), [Sharing](https://help.krisp.ai/hc/en-us/articles/10386573495196-Sharing-your-meetings-with-Krisp)

Krisp remains a clean-room behavior reference only. GRAF does not copy its
visual expression, brand, assets, wording, layout, or implementation.

## Target IA

Feature 121 adds no new global destination.

```text
GRAF
├── Встречи
│   ├── список + поиск
│   └── встреча
├── Запись — постоянный нативный слой, не раздел навигации
│   ├── начать
│   ├── пауза / продолжить
│   └── остановить
└── Настройки
    ├── микрофон
    ├── определение встреч
    ├── формат итогов по умолчанию
    └── все форматы итогов

Встреча
├── Итоги
├── Расшифровка
├── Поделиться…
└── Ещё
    ├── Экспортировать…
    ├── Скачать аудио…
    ├── Сведения о встрече…
    └── Удалить встречу…
```

### Always visible

- the content for the current task;
- one primary action;
- local recording status and one-action Stop while capture is active;
- one short current meeting status when it changes what the user can do.

### Revealed on request

- microphone selection;
- all summary formats and personal-format management;
- who has access and what they see;
- export formats;
- technical meeting provenance and lifecycle details.

### Revealed only when relevant

- lost source and recovery;
- insufficient local storage;
- sign-in needed to resume sync;
- terminal upload/transcription/summary failure;
- stale revision conflict;
- broader-sharing consequence;
- deletion boundary.

### Never shown as product UI

- provider names, job IDs, attempt counts, object keys, token rotation internals,
  RLS state, audit rows, manifest structure, or queue state names;
- one aggregate percentage fabricated from independent artifact pipelines;
- a matrix of audience × content × role × download × export on the first Share
  screen.

## One Primary Action Per State

| State | Primary action | Secondary action | User-facing status |
|---|---|---|---|
| Permission missing | `Разрешить доступ` | `Позже` | Name one permission and why it is needed |
| Ready | `Начать запись` | None | `Готово к записи` |
| Meeting detected | `Начать запись` | `Не сейчас` | `Похоже, началась встреча` |
| Starting | None | `Остановить` remains reachable | `Начинаем запись…` |
| Active | `Остановить` | `Пауза` | `Идёт запись · 12:34` |
| Paused | `Продолжить` | `Остановить` | `Запись на паузе · 12:34` |
| Saving | None | None | `Сохраняем запись на Mac…` |
| Saved offline | None | `Открыть встречу` | `Сохранено на Mac. Отправим при подключении.` |
| Background processing | Open ready content | None | One specific current result, such as `Готовим итоги…` |
| User-recoverable failure | `Повторить` or the specific recovery | None | Explain the result and next action, not the subsystem |
| Meeting ready | Read `Итоги` | `Поделиться` | No success dashboard or lifecycle stepper |
| Delete confirmation | `Удалить встречу` | `Отмена` | State the GRAF-controlled scope and external-copy limit |

Stop is immediate and has no confirmation. Delete and broader sharing are the
only normal-path actions that require consequence confirmation. Plain Escape
closes a popover or dialog and MUST NOT stop recording.

## End-To-End Scenario Matrix

### Before capture

| Scenario | What the user sees | What GRAF does silently |
|---|---|---|
| Returning user, healthy | `Готово к записи`, `Начать запись`, quiet `Системный звук и микрофон` | Reuses last valid microphone and safe defaults |
| First use | One permission explanation and system request at a time | Rechecks after returning from macOS Settings |
| Microphone denied | `Разрешите доступ к микрофону` → `Открыть настройки macOS` | Keeps system audio readiness separate |
| System audio denied | Equivalent copy naming `Системный звук` | Keeps microphone readiness separate |
| Both denied | Resolve one permission, then the other | Never presents two competing errors |
| Low disk safety gate | `Освободите место перед записью` → `Открыть хранилище` | Calculates the threshold without exposing it by default |
| Workspace policy blocks | `Запись недоступна в этом рабочем пространстве` | Does not leak policy identifiers |
| Offline | Quiet reassurance that recording works offline | Defers server work |
| Meeting detected | Small nonmodal prompt with `Записать сейчас`, `Пропустить`, `Всегда писать это приложение`, and an eight-second countdown | Target identity, policy and capture-gate details |
| Detection becomes stale | Prompt disappears; manual Start stays | No timeout error |
| Duplicate Start | Button immediately becomes `Начинаем…` | Idempotently creates one session |
| Recording already active | Current recording opens; no second Start exists | Rejects a second session |
| User wants another microphone | Opens quiet `Микрофон` control | Uses macOS default otherwise |
| Normal silence | Remains ready/healthy | Does not treat a quiet level as missing hardware |

The paragraph above is the historical Feature-121 simplification and is
superseded for verified native targets by Feature 124. The current
`MeetingDetectionPromptView` intentionally restores the eight-second countdown,
automatic start on expiry, immediate start, skip, and target-scoped
`Всегда писать это приложение` opt-in. It still never starts from arbitrary
audio, an unknown app, or a blocked capture/policy state.

### Active capture

| Scenario | What the user sees | What stays hidden |
|---|---|---|
| Starting | `Начинаем запись…`; Stop is available | Writer/package creation |
| Active | Text status, timer, Pause, Stop | Upload/processing controls |
| Pause | Immediate text change; Resume replaces Pause | Privacy-interval storage |
| Resume | `Продолжаем…`, then Active | State-transition mechanics |
| Stop | Immediate transition to saving | Finalize sequence |
| Repeated rapid controls | Temporary busy label; buttons reject invalid repeats | Transition conflict handling |
| Microphone lost | `Микрофон не записывается. Системный звук продолжается` + `Выбрать микрофон` | Device IDs and raw errors |
| System audio lost | Exact equivalent naming system audio | Generic `degraded` jargon |
| One source survives | Recording continues if safe; warning stays | No claim of complete capture |
| Device changes | `Проверьте микрофон` when continuity is unproven | No false seamless-switch claim |
| Network/auth lost | `Запись продолжается на Mac` | Login walls and server health |
| Mac sleeps | On resume, state exactly what was preserved or missed | No continuity guess |
| Duration/storage limit | Safe automatic stop and reason | Threshold details until needed |
| App closes or crashes | Relaunch shows one recovered meeting/action | Reconciliation and deduplication |

### Saving, sync, and processing

| Scenario | What the user sees | Automatic behavior |
|---|---|---|
| Stop succeeded | Meeting appears immediately as `Сохранено на Mac` | Durable local finalization first |
| Online | `Синхронизируем…` only while useful | Resumable upload |
| Offline | Local playback and `Отправим при подключении` | Retry when network returns |
| Auth expired | `Войдите, чтобы продолжить синхронизацию` | Local copy remains safe |
| Temporary failure | No premature repair button | Bounded automatic retry |
| User action required | One concrete recovery button | Stops automatic retries only when appropriate |
| Duplicate finalize/upload | One meeting remains | Idempotent server acceptance |
| Transcript ready first | Opens transcript; `Итоги готовятся` | Independent artifact state |
| Playback ready first | Player works while text is pending | Independent artifact state |
| Summary fails | Audio/transcript stay usable; `Повторить` near Итоги | Accepted prior result remains current |
| Terminal partial result | Shows usable artifacts and one next action | No generic full-page failure |

The meeting list uses one human status only: `Сохранено на Mac`,
`Синхронизируем…`, `Готовим расшифровку…`, `Готово`, `Частично готово`, or
`Нужно действие`. Detailed pipeline stages stay under `Сведения о встрече…`.

### Review

| Scenario | Behavior |
|---|---|
| Everything ready | Open `Итоги` by default |
| Transcript ready, summary pending | Open `Расшифровка`; show quiet `Итоги готовятся` |
| Only audio usable | Show player and a direct text explanation |
| Partial result | Ready content works; no aggregate red state |
| Timestamp selected | Seek player and highlight the matching turn |
| Playback position changes | Active transcript turn follows the same timeline |
| Unknown speaker | Show `Спикер 1`, never invent an identity |
| Speaker correction | Edit inline from the transcript toolbar/name |
| Browser and desktop cabinet | Same server truth; native capture strip remains above embedded content |
| Reload after revoke/delete | Content closes on the next request |
| Narrow window | One column; player and active Stop stay reachable |

Meeting detail contains no permanent right rail. It contains title/date/duration,
one current status, Share, More, persistent player, and exactly two content tabs:
`Итоги` and `Расшифровка`. Search appears only inside `Расшифровка`.

### Summary formats and versions

| Scenario | Simple behavior |
|---|---|
| Normal meeting | `Авто` selects the default format; no decision is required |
| Open format selector | Up to four recent/relevant choices + `Все форматы…` |
| Manage personal formats | Settings owns create/edit/duplicate/archive/delete |
| Customize built-in | `Создать копию`; built-in stays immutable |
| Select another format | Start a background candidate while the accepted result remains visible |
| Candidate ready | `Новый вариант готов` → `Использовать`; dismiss keeps current |
| Candidate fails | Current result stays; local `Повторить` appears |
| Stale acceptance | `Итоги уже изменились. Обновите страницу.` |
| Shared meeting | Recipient sees only the accepted rendered result, not format settings |

Do not show language, detail level, section keys, and format version together in
the quick selector. Do not show permanent `Сгенерировать снова`. GRAF avoids the
destructive behavior documented by Krisp: generation creates a candidate and
does not replace accepted or manually edited notes until the owner chooses
`Использовать` after the new result exists.

### Candidate lifecycle and regeneration matrix

The user sees one calm current result and, only when relevant, one pending or
ready alternative. The server retains every revision; the main page never
becomes a version-management dashboard.

| Situation | User action / visible state | Automatic behavior | Accepted result |
|---|---|---|---|
| First usable transcript, no accepted result | Quiet `Готовим итоги…` | One policy-owned `Авто` candidate | None yet; transcript stays usable |
| First candidate succeeds | `Новый вариант готов` (or existing deterministic итог remains current) | No second hidden format/classifier call | Candidate is accepted only by the existing explicit initial policy; otherwise owner chooses `Использовать` |
| Owner chooses another format | `Готовим формат «…»` | Reuse one durable candidate/workflow on retry | Remains current |
| Candidate ready | `Новый вариант готов` with preview, `Использовать`, `Оставить текущие` | No auto-accept | Remains current until explicit accept |
| Candidate transiently fails | `Не удалось подготовить…` + concrete retry | Retry same candidate only, bounded by workflow policy | Remains current |
| Candidate invalid/stale/deleted/ambiguous | Reason + one recovery action, no blind retry | No automatic new candidate | Remains current |
| Reload, second tab, or new owner device | Server restores pending/ready candidate | Session storage is only a cache | Unchanged |
| Transcript/source revision changes | Candidate marked unusable; `Обновить расшифровку` or explicit new request | Cancel before egress/publication | Remains current |
| Owner accepts ready candidate | One confirmation-free `Использовать` action | Atomic expected-pointer check | New set becomes current; old set is superseded |
| Owner dismisses/rejects | Candidate leaves primary view; history remains owner-only | No deletion and no regeneration | Unchanged |
| Prompt/model/template/share changes | No surprise UI change | Existing candidates keep pinned provenance | Unchanged |
| Shared viewer opens meeting | Only accepted summary is rendered | Never exposes candidates or templates | Unchanged |

The selector therefore distinguishes `Текущие итоги: <format>` from
`Готовим вариант: <format>`. Selecting the already-current format is a no-op;
creating another version is an explicit `Создать новый вариант` action, not a
hidden repeat request.

### Sharing

The first Share surface answers only:

1. Who should get access?
2. What will they see?
3. Who already has access?

Default: invite-only, summary-only, view-only.

| Scenario | Simple behavior |
|---|---|
| Open Share | Person/email field, `Пригласить`, current viewers, quiet `Что увидят: только итоги` |
| Invite internal person | Select and invite; show `Доступ отправлен` and add one row |
| Paste several addresses | Chips and one send action |
| Self or duplicate | Inline `У этого человека уже есть доступ` |
| Unknown/external address unavailable | Neutral inline failure without account enumeration |
| Change content for a recipient | `Только итоги` or `Вся встреча`; explain that full includes audio + transcript |
| Revoke | Row action `Удалить доступ`; next request is blocked |
| Copy invite-only link | Only from an existing recipient row; it remains recipient-bound |
| No recipient-bound grant | No ambiguous global Copy link appears |
| Broader workspace/team access | Hidden under `Изменить общий доступ`; confirm the real audience |
| Anyone-with-link disabled | Option is absent, not disabled clutter |
| Anyone-with-link enabled | Separate `Доступ по ссылке → Включить`; default content remains summary-only |
| Rotate or revoke public link | `Создать новую ссылку` / `Выключить`; state the effect on the old link |
| Expired/revoked/wrong viewer | Generic `Встреча недоступна` without content metadata |

Role is fixed to `Просмотр` in this slice. Download/export are owner actions and
are not first-screen Share toggles. If a later validated need requires recipient
download, expose one `Разрешить скачивание` control inside that recipient's
advanced row, not a global capability matrix.

### Export, delete, and denied states

| Scenario | Behavior |
|---|---|
| Export | `Ещё → Экспортировать…`; show only ready canonical formats |
| Download audio | Separate clear action from text/data export |
| Viewer without capability | Action is absent, not a disabled cockpit row |
| Export processing | `Готовим файл…`; dialog may close safely |
| Delete | `Ещё → Удалить встречу…`; one named confirmation |
| Deleting | Hide content/actions immediately; `Удаляем встречу…` |
| List after delete | Remove the accepted row and close the dialog; do not render a persistent success/cleanup banner |
| Deleted | Remove from normal list; do not promise deletion of external copies |
| Delete races | `Удаление уже началось`; no new share/generation/export publication |
| Missing, denied, revoked, expired, deleted | Same safe `Встреча недоступна` shell |
| Authentication expired | `Войдите, чтобы продолжить`, then return to the intended path |

## Accessibility And Responsive Contract

- Text communicates Active, Paused, Error, Saved, and Ready; color and animation
  are never the only signal.
- Status changes are announced without moving focus and without announcing the
  timer every second.
- Modal focus enters the first useful control, stays inside, closes with Escape,
  and returns to its opener. Escape never stops an active recording.
- Primary controls target 36–44 px or larger; visible focus is never clipped.
- Reduced Motion removes pulses and nonessential transitions.
- At narrow width, secondary actions move to `Ещё`; primary action, active
  recording status, player, and Stop remain visible.
- Loading buttons keep their size and use direct text such as `Сохраняем…` or
  `Приглашаем…`.
- Errors appear next to the affected field/action and use Russian product copy,
  never raw provider/debug text.

## Prototype Contract

The interactive prototype MUST cover one connected flow with these 12 states:

1. ready;
2. one-permission recovery;
3. detected meeting with the Feature-124 countdown/autostart contract for a
   verified target, and no start for unknown or blocked activity;
4. active recording;
5. paused recording;
6. degraded source while the other source continues;
7. saved locally/offline;
8. partial processing;
9. ready summary meeting detail;
10. format candidate ready while accepted summary is preserved;
11. simple internal Share and revoke;
12. delete plus generic denied/deleted state.

Every frame passes only when a user can answer within a few seconds:

- What is happening?
- Is my recording safe?
- Does GRAF need me to do anything?
- What is the one next action?

The prototype MUST demonstrate template and Share overlays separately, never
open together. Synthetic data only; no competitor identity, real person, email,
meeting text, or private artifact may appear.
