# T119 Round239 — ограниченная проверка исходников shim, 2026-10-05

**REQUEST CHANGES: C0 / H0 / M1 / L0.** M1 блокирует source approval этого
среза. Это не пересмотр принятого requirements gate и не приёмка T119 целиком.

Canonical worktree: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Fresh read-only branch/HEAD: `codex/200-windows-followup`,
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`. Dirty работа других участников
сохранена. Reviewer пишет только этот новый report; code/norms/tasks/checklist
markers/Git/GitHub/старые reports не меняет.

## Граница и метод

Лично прочитаны текущий embedded kDesktopBridgeScript, Host.h, host publication/
dispatch/reply/cancellation/revoke, NavigationStarting/close/process-failure/
runtime/nonce/bootstrap callers, оба тестовых файла целиком и локальный diff.
Round238 host source acceptance использована как ограниченная исходная точка,
без нового аудита остальных частей Feature200. Trace всех production callers
setCalendarJoinHandlers подтверждает: AppMain ещё не подключает callbacks.

Лично прочитаны code-reviewer, ponytail-review, frontend-code-review и все три
обязательных references последнего. React/Tailwind/React Flow правила к этому
vanilla JS не применяются. Применены correctness/security/error-path/DOM/a11y и
минимизация diff, без создания нового интерфейса или framework. Ранее лично
прочитанные AGENTS/constitution/guidance сверены по неизменным hashes. Высокорисковая
полоса T119 сохранена; ограниченная запись reviewer report не снижает её.

Основание — принятый shim appendix wire gate: строки293–397, SHA-256
`be877de3d641b283857a6ce1855a724293a999c26cc5a9814b1f42f54b283dfb`,
bridge §4/§10 и plan T119 wire sequence. Readiness требует handshake **и**
native presentation; JS флаг не является authority. Новой schema нет.

## Code review

Found 1 urgent issue need to be fixed:

### M1 — повторная публикация может включить presentation при отключённом native allowlist

FilePath: `apps/windows/RecApp/Web/WebView2Host.cpp`, line1086
(ветвь ошибки1089–1091; повторный caller2083).

```cpp
nativeRunScript_(calendarJoinHandler_ && calendarCancelHandler_ &&
    policy_.evaluate(currentUrl_).kind == RouteKind::meetings
    ? "window.__grafSetCalendarJoinAvailable?.(true)" : "window.__grafSetCalendarJoinAvailable?.(false)");
// catch:
bridge_.setCalendarJoinEnabled(false);
```

Конкретный путь: обе callbacks установлены на meetings; публикация бросает,
catch отключает calendar allowlist, сохраняя callbacks. Затем исходный
bootstrap completion повторно вызывает publishCalendarJoinAvailability, и
публикация теперь успешна. Условие снова выбирает `true`, но allowlist остаётся
false: ни эта функция, ни rotateNonce не восстанавливают calendarJoinEnabled.
Trusted click после native_ready создаёт JS pending/resolving и подавляет
standalone; bridge.validate отвергает calendar_join как commandDenied без reply.
Получается зависший pending до отдельного disable/DOM/nonce события.

Это source-level error-path counterexample, не заявление о воспроизведении на
установленном WebView. Он относится к публичному setter и уже существующему
post-bootstrap replay, а не к отсутствующей будущей AppMain реализации.

### Suggested fix

Минимально согласовать публикацию с фактическим native разрешением через
existing WebViewBridge::isAllowedWebCommand("calendar_join") вместе с текущими
callbacks/route guards. Альтернатива — явно и согласованно восстановить
allowlist, но не публиковать `true` при сохранённом fail-closed denial.
Новый service/state framework не нужен.

В existing friend fixture добавить сценарий transient publication throw →
успешный повтор publish (как bootstrap) → проверка согласованности presentation
и native dispatch. При выбранном fail-closed поведении повтор должен публиковать
false, не принимать Join; явный последующий setCalendarJoinHandlers может
восстановить работу. Тест94–98 сейчас проверяет только немедленный denial после
постоянно бросающего callback; successful replay не покрыт.

Found 0 additional suggestions for improvement.

## Подтверждённые исходниками свойства и границы

- JS первоначально disabled; до nonce **или** при disabled availability нет
  pending/preventDefault. После barrier capture listener принимает только
  trusted click, в том числе штатную keyboard activation anchor/button;
  synthetic .click() не отправляет intent. Точные UUID и payload3/2keys,
  URL/href/Record не передаются. One local pending не заменяет native busy lease.
- Reply проверяет nonce/request, текущий canonical event/actionable DOM до
  применения результата, known states/reasons; нельзя перескочить opening или
  возродить terminal. Поздний старый request не снимает новый. Перед обработкой
  reply повторная DOM-проверка закрывает окно до MutationObserver microtask.
- Итоговый DOM с доступным same canonical UUID сохраняет pending; removal,
  replacement, hidden/inert/disabled/UUID mutation отменяют его. Map хранит
  только собственные aria изменения, удаляет disconnected элементы и при
  terminal восстанавливает прежнее aria-disabled у ещё существующих кнопок.
  Status использует textContent, role=status/aria-live=polite и русские строки;
  штатные keyboard/focus semantics не заменены synthetic key framework.
- Disable/pagehide/nonce change снимают local pending, matching cancel содержит
  только eventId/requestId. postMessage throw у Join снимает pending и показывает
  failed; cancel send throw не объявляет drain. Native guard/parser/replay1024
  остаются authority, а не JS presentation flag.
- Handler replacement сначала отключает native calendar authority и отменяет
  прежний pending; revoke отменяет перед generation/nonce/alive/runtime отзывом.
  Fixed-literal publication reused nativeRunScript; bootstrap replay присутствует.
  native_ready payload остаётся пустым объектом. Известная M1 выше относится к
  согласованности именно failure/replay пути, не к расширению handshake.
- Round238 matching pending identity и reentrant catch fence сохранены; новая
  публикация не добавляет URL/token/raw-exception logging, resolver/OS launch,
  auth или Record. AppMain/common card/menu owner и installed workflow не wired.

## Ponytail review

Lean already. Ship. Это только оценка сложности diff, **не** source approval
при открытом M1. Existing script/channel/MutationObserver/nativeRunScript и
Map/UUID reused; второго bridge/client/factory/новой зависимости нет. Удалять
security/DOM-current guards или regression assertions ради сокращения нельзя.

## Точные bytes и receipt граница

SHA-256 свежего чтения после mechanical MSVC literal split:

| Файл | SHA-256 |
| --- | --- |
| apps/windows/RecApp/Web/WebView2Host.h | `fbab2a1399831f0a31ae48b86997ec07468c82f23a4daffa4e55701057e98dd0` |
| apps/windows/RecApp/Web/WebView2Host.cpp | `667e61151685f2386bf5d18772e725d56b9a879ecc8f6a201cdfb446b24d70bb` |
| apps/windows/Tests/GrafWindowsContractTests/CalendarJoinHostTests.cpp | `67bb8a2ac33cab2d49bafe3f79e9d00229483f49f15c5c9094c9f620666cb73b` |
| apps/windows/Tests/GrafWindowsContractTests/CalendarJoinShimTests.cjs | `18d9fed4e4e9f844eb88266ea6a0b3edba777ec65c05dabdd448546c13c1b40d` |

Первое чтение подтвердило submission Host.cpp
`0521048c1d52e48cc8fd7b2f60c68c5077b9527f33e7a7751711c139674c8bbf` и
shim test `f2802d15568330a057ce34f1fe0594af2bab34b784dde4193de0a2a5f1f0042c`.
Main сообщил actual SDK RED12907 C2026: один wide literal слишком длинный.
После изменения один constant состоит из двух adjacent raw literals, граница
после calendar click listener сохраняет JS concatenation без изменения логики;
тест теперь извлекает все chunks и проверяет wide-byte ceiling16380 каждого.
Compile retry/последующие final-byte browser/native receipts на момент review
не предоставлены: literal repair не объявлен actual SDK GREEN только по тексту.

Браузерный тест127+строк лично прочитан: Chromium/WebKit real click/Enter через
Playwright, fake document/channel/reply. Он покрывает barrier, synthetic denial,
repeat click, transitions, stale reply, HTMX same/replaced/removed UUID, nonce/
disable/not-ready, aria cleanup, attribute mutation, reply-before-observer race
и postMessage throw. Это не native WebView channel, installed keyboard/a11y,
AppMain auth/owner/launcher proof. Test jobs reviewer не запускал и не дублировал
main; reported pre-final45/49/SDK/initial browsers receipts остаются историей,
а не PASS текущих hashes.

**Terminal: REQUEST CHANGES C0/H0/M1/L0; единственный source blocker — M1.**
Requirements wire5/0, operation8/0, launcher5/0 здесь не перемаркированы;
T119/issue7540 не закрываются. Старые reports и все чужие dirty bytes сохранены.

## Последняя ограниченная test receipt — 2026-10-05

Main усилил только existing publication-throw assertion; лично перечитаны
строки91–99 текущего CalendarJoinHostTests.cpp. После send2 проверяются также
history==1/replies.size()==2, поэтому no-op owner больше не маскирует ошибочную
admission. SHA-256 этого файла теперь
`d0d56007e74e6e954cc482ed15f9dc546f8fbc69e56d6cf74f54d713b092bb0a`;
предыдущий hash в таблице остаётся историческим снимком первого чтения.
Host.h/Host.cpp/shim.cjs заново сверены — hashes таблицы неизменны.
Эта проверка покрывает immediate denial, но не successful bootstrap replay;
M1 этим усилением не исправлен и остаётся открытым.

Main сообщил browser9672 final adjacent-chunks **2/2 PASS** (Chromium/WebKit).
Это owner-reported fake-channel browser receipt, reviewer не запускал его
повторно. Native66201 49/49 PASS260.62s — pre-chunks bytes;
portable54479 45/45 PASS22.72s — pre-strong-assert bytes. Финальные reruns и
SDK74144 ещё pending по полученной квитанции; SDK C2026 retained как история.
Отдельных product/installed/real-WebView claims не сделано.

**Последний bounded verdict: REQUEST CHANGES C0/H0/M1/L0.** Only blocker M1;
тестовое усиление принято, но не заменяет исправление publication/replay.

## M1 closure — bounded recheck, 2026-10-05

**APPROVED, source only: C0/H0/M0/L0; M1 CLOSED.** Предыдущие findings/verdicts
и receipts выше сохранены как история. Перед append report лично перечитан
целиком; прежний SHA-256:
`b7138543a86705a643589fc7ac307366f3339c1c3b21664e718746b4f934f7be`.
Fresh read-only canonical branch/HEAD снова совпали:
`codex/200-windows-followup`, `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.

Лично перечитаны только изменённое условие publish, существующая реализация
WebViewBridge::isAllowedWebCommand и fixture wrapper/regression. Code-reviewer
и ponytail-review прочитаны полностью и применены к этому delta; новый широкий
source/requirements review, browser/native/build jobs не запускались.

В Host.cpp:1086 добавлен один guard
`bridge_.isAllowedWebCommand("calendar_join")`; callbacks и meetings route
условия сохранены. Этот existing query не меняет message-id/history/nonce и
возвращает calendarJoinEnabled. После publication throw catch оставляет
native denial; subsequent successful replay теперь выбирает fixed literal
false, а не true. Explicit setter вновь согласованно включает allowlist при
обеих callbacks и публикует true. Исходный M1 counterexample устранён, нет
автоматического retry/authority восстановления или новой schema/interface.

CalendarJoinHostTests.cpp:67 даёт wrapper только существующей friend fixture,
не production API. Строки99–106 проверяют transient throw → successful replay
false → send2 без history/reply роста → explicit setter true → send2 admitted
с accepted.size()==2/history==2. Вместе с assertions95–98 это проверяет именно
M1, а не неизменный accepted vector no-op callback. Capturing publication
callback сбрасывается до разрушения локальной строки, lifetime соблюдён.
Main сообщил focused test-first32886 **RED exit8** на published==false, когда
old implementation публиковала true; это owner-reported receipt. Нового actual
GREEN для latest bytes в текущем сообщении нет, и reviewer его не выдумывает.

Дополнительная read-only whole-file проверка минимальности: удаление только
одного добавленного guard из текущих bytes в памяти даёт предыдущий Host.cpp
SHA-256 `667e61151685f2386bf5d18772e725d56b9a879ecc8f6a201cdfb446b24d70bb`.
Удаление только fixture wrapper и regression99–106 в памяти даёт прежний test
SHA-256 `d0d56007e74e6e954cc482ed15f9dc546f8fbc69e56d6cf74f54d713b092bb0a`.
Следовательно, embedded JS/bootstrap/lifecycle и остальные test bytes этим
исправлением не менялись; никаких файлов для проверки не создавалось.

### Latest source SHA-256

| Файл | SHA-256 |
| --- | --- |
| apps/windows/RecApp/Web/WebView2Host.h — unchanged | `fbab2a1399831f0a31ae48b86997ec07468c82f23a4daffa4e55701057e98dd0` |
| apps/windows/RecApp/Web/WebView2Host.cpp | `db5c6371709f3ef97db74802deb7184028ffa13296b4a90fb9b8de774dd4a3f3` |
| apps/windows/Tests/GrafWindowsContractTests/CalendarJoinHostTests.cpp | `27f9386d6af5181649738066181a46ff3d905ee593995d959e99ad0a71eb701c` |
| apps/windows/Tests/GrafWindowsContractTests/CalendarJoinShimTests.cjs — unchanged | `18d9fed4e4e9f844eb88266ea6a0b3edba777ec65c05dabdd448546c13c1b40d` |

Ponytail: Lean already. Ship. Только оценка минимальности source fix: reused
existing bridge query, один guard, fixture-only regression; нет нового слоя
или зависимости. Это не разрешение installed/release handoff.

SDK74144 PASS до M1 сохранён как исторический, не latest-source SDK acceptance.
Текущий native24638 и запланированный latest-byte rerun, final browser/portable
jobs ещё не имеют финальной квитанции в текущем сообщении main. Independent
CoreTests46277 exit255 на writeResult.ok/fixed-temp path — отдельный reported
отказ с **неустановленной причиной**; никаких выводов о race/невиновности,
PASS или снятии validation blocker не сделано. По main rerun будет после49CTest;
reviewer не запускает параллельную проверку и не исследует этот иной scope.

**Terminal bounded source verdict: APPROVED C0/H0/M0/L0, M1 closed.**
Actual final native/SDK/portable receipts остаются отдельной validation границей.
AppMain не wired, installed/auth/OS launch/Record и whole T119 не приняты.
Изменён только append этого reviewer-owned report; нормы/tasks/markers/code/
Git/GitHub/чужие dirty bytes и прежняя часть отчёта сохранены.
