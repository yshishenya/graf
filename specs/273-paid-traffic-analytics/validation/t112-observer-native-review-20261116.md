# T112 — независимое ревью observer/native

Дата:16.11.2026. Проверяющий: `/root/public_counter_readiness_review`.
Полоса: `high-risk-product`, незавершённый изолированный T112.
Основа: `13edb699c1cee3c9b40808b44d3d8d3b0ba01852` плюс рабочие файлы
с точными хешами ниже. Предварительный проект и22 строки уточнения договора
проверены до кода в собственном observer/native preflight.

## Решение

**PASS независимого чтения кода данного шага; P1=0, P2=0.**
Блокирующих дефектов в проверенном observer/native diff не найдено.
Завершённые серверный и Swift-профили прочитаны ниже; все семь проверенных
хешей повторно совпали. Это не закрытие полного T112/T113 и не замена ручной
GRAF Dev приёмки или точных выпускных проверок.

Повторно проверены13/13 неизменных документов требований/checklists/analyze
и изменённый договор. Договор соответствует принятому preflight SHA-256
`ee1005b6a59ad1b42f0b7d0af25dd7099c8337a4d11930a3aba9ee6479d270d8`.
Списки повторно пересчитаны:16/0,27/0,52/0,29/0 — **124/0**, без изменения
отметок. Это требования, не выполнение всего T112.

## JS: наблюдение и асинхронные границы

Прочитан весь добавленный observer, его полный diff, browser fixture и
Python wrapper. Прежние unrelated observer/recording очереди не используются
как доказательство результата.

- Наблюдение отключено во frame и без IO/MutationObserver. Root допускает
  только canonical browser/desktop own detail UUID path, соответствующие
  meeting ID и embedded flag. Shared/action/другие пути не проходят.
- Proof принимается только ограниченного формата≤1536 ASCII bytes. Выбран
  только конкретный `div.text`/`p.outcome-item-text`, а не heading/container.
  Проверяются непустое тело, connectedness, rect/client rects, IO intersection,
  viewport, hidden/inert/aria-hidden/closed details, display/visibility/
  opacity/content-visibility ancestors, document visible/focus/not-prerender.
- Перед отправкой выполняются два RAF. После каждого асинхронного шага
  проверяются generation, текущие node/root/path/query/proof/CSRF и видимость.
  Native reply дополнительно привязан к nonce. Удалённый/заменённый root,
  изменённый proof/CSRF/query и pagehide обесценивают ожидающее действие.
- Собственный endpoint получается только из проверенного pathname плюс
  `/result-viewed`. POST содержит единственное поле proof, same-origin
  credentials, CSRF, no-store, redirect:error и AbortController с2s бюджетом
  native+HTTP попытки. В теле нет текста, identity, account, source kind,
  arbitrary URL или частных meeting/result references.
- Ответ допускается только HTTP200 application/json без redirect; поток
  ограничен2048bytes и строгим UTF-8. После каждого чтения проверяется
  актуальность/видимость. Reader отменяется при завершении/ошибке.
  Только точная форма accepted завершает попытки блока; точный renewed
  с новым bounded proof разрешает одно обновление за переход видимости и
  новую RAF/native проверку. Неизвестные/лишние поля и транспортные ошибки
  не объявляют успехом и не запускают немедленный retry.
- attempted/done/renewed находятся только в памяти текущего документа.
  Неизменный native refresh/новый nonce не сбрасывают attempted, query и
  CSRF changes также не становятся новым показом. Настоящий уход из
  видимости/возврат либо native false→true допускает следующую попытку.
  Unknown/disconnected bridge приостанавливает без выдуманного перехода.
- MutationObserver удаляет detached/stale состояния и abort/unobserve;
  HTMX swap/settle, geometry/focus/visibility изменения повторяют проверки.
  Pagehide выключает observer и прекращает текущие действия; pageshow
  возвращает наблюдение с реальной новой проверкой. Нет timer retry,
  beacon/localStorage/UserDefaults или очереди для ушедшего документа.

## Native: полномочия, foreground и lifecycle

Прочитан целиком новый bridge и его тесты, весь lifecycle diff coordinator
и применимые activation/reconciliation/navigation/detach участки.

- WK принимает только `{version:1,nonce}`. Лишние поля, неверные типы,
  version/nonce, subframe/loading, чужой source/current path/origin/view
  отвергаются. Проверяется `message.webView === attached webView`, текущий
  document guard и `DesktopCabinetSessionBridge.isCurrentSession()`.
- `isDetailURL()` требует точный lowercase UUID canonical encoded path
  `/desktop/meetings/{UUID}` и same-origin route allow. Broad meetingDetail
  kind не используется самостоятельно: shared/public/actions/encoded aliases
  исключены. Собственные detail query/fragment не превращаются в POST target.
- Активация выполняется из guarded synchronize после auth-navigation/cookie
  reconciliation; generation берётся после этого и без navigation barrier.
  Старые completion/другой document revision/attached view/loading/terminated
  coordinator не активируют текущую поверхность.
- Handler возвращает только version и ready Bool; отказ содержит лишь
  фиксированное unavailable, без identity/proof/content. Он не вызывает сеть,
  admission, capture или файловое чтение. Foreground вычисляется на MainActor
  по app active, view attached/nonhidden, window visible/nonminiaturized и
  visible occlusion state. Отсутствующее окно даёт false.
- Navigation start, detach и content termination явно invalidate bridge;
  auth-session notification также invalidate. Nonce/generation/document guard
  сбрасываются, JS получает disconnect. Native app/window notifications
  вызывают только refresh; повторный положительный ответ не создаёт событие.
- Handler регистрируется/снимается вместе с другими WK bridges. Старый
  клиент без handler/activation не измеряет результат; просмотр/запись не
  требуют успешного ответа нового моста.

## Причинное покрытие и реально прочитанный результат

Browser fixture исполняет общий настоящий cabinet.js на синтетических
страницах Chromium/WebKit. Покрыты видимый body,17 hidden/empty/metadata/
invalid-proof случаев, document visibility/prerender/focus, no-CSRF/shared/
old client, processing→ready/HTMX, no automatic retry, one renewal,
detached late response, native false→true, continuous refresh/nonce/query/
CSRF и async interruptions root/proof/nonce/focus/CSRF/pagehide.
Native tests покрывают exact paths, malformed/subframe/loading/wrong nonce,
все5 foreground prerequisites, настоящий WK read-only reply, generation
barriers, current document invalidation и coordinator reconciliation/три exits.
Unit foreground predicate не заменяет ручную проверку GRAF Dev/window.

Прочитан завершённый серверный журнал
`/private/tmp/graf-t112-visibility-server-20261116.log`:
**158 passed,1 прежнее PytestAssertRewriteWarning,25.65s**, без skip.
Wrapper параметризован Chromium/WebKit и падает при ненулевом exit browser
runner. Оба движка завершили проверку; точное число browser scenarios этот
журнал не печатает, поэтому отдельное количество здесь не утверждается.
Reviewer не перезапускал тесты и не выдаёт чтение чужого журнала за свой запуск.

Прочитан завершённый Swift-журнал
`/private/tmp/graf-t112-visibility-swift-20261116.log` с SHA-256
`dbaf7ad25ce19d0b5cf553f6291fdb19c89b5ed664f7ac84d0da431bbda7bc00`:
**69 tests,0 failures,11.699s**. В том числе все5
`EmbeddedCabinetResultVisibilityTests` завершились успешно. Исполнитель
отдельно подтвердил EXIT0. Fixture использует isolated notification presenter,
что ранее проверено чтением теста; прежний crash не считается успешным
прогоном. После завершения повторно вычислены все семь хешей из таблицы:
совпали полностью. Живая session8194 reviewer не опрашивалась; повторный
запуск тестов не выполнялся.

Прочитана квитанция `/private/tmp/graf-t112-visibility-html-20261116.json`:
12/24 HTML совпадают буквально, остальные12 отличаются только версией URL
`cabinet.js` (`ed427987adad`→`94189c0aba20`); после замены только этой версии
совпали24/24. Это результат сравнительного прогона исполнителя, а не
самостоятельный повторный рендер проверяющего.

## Оставшиеся границы полного результата

В этом diff нет production issuance/render proof mapping, серверного POST
handler или общей T113 admission. Обычный рабочий сбор off; настоящий отказ
recovery/readiness не снят. Synthetic replies не доказывают durable accepted,
оплату, нового внешнего клиента или T0. Эти части, DB/concurrency/failure
матрица, ручной GRAF Dev и release gates остаются обязательными. Возможность
наблюдать штатный показ не доказывает прочтение человеком и не защищает от
намеренной подделки владельцем собственного клиента.

Изменён только настоящий review report. Код/spec/plan/tasks/checklists,
Git/GitHub, runtime, приложения и публикации проверяющий не менял.

## SHA-256 проверенного рабочего среза

| Путь | SHA-256 |
| --- | --- |
| `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js` | `94189c0aba20a78b4ef38c8c273fcf8aab3dd8965fff8ba16d1229537610915c` |
| `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetResultVisibilityBridge.swift` | `edf74987840bda0c6ebb4e175a3157796fe630cc0172ba7b9d2780ce32d71c2c` |
| `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift` | `3685554032cc3eeb044b5f227d3eb671d6c988d69b1c65bfce4492e6d3d9df74` |
| `apps/macos/Shared/Tests/EmbeddedCabinetResultVisibilityTests.swift` | `9ace22f64ab735815a07e0918262f8f5295d1fbbc1e21465d348c6fd468186b1` |
| `apps/server/tests/browser/result-visibility.test.cjs` | `0420c58dc17115bcfaa8c6bd7f284f6f448fd44fec178eff2efaeb7d5d68cab2` |
| `apps/server/tests/contract/test_result_visibility_observer.py` | `bcbb2e0e56786872960cd77aa11b15bd8c972566cb180984bc1763bac66ab856` |
| `specs/273-paid-traffic-analytics/contracts/result-visibility.md` | `ee1005b6a59ad1b42f0b7d0af25dd7099c8337a4d11930a3aba9ee6479d270d8` |
