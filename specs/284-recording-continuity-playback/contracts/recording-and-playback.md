# Contracts
- Native metadata snapshots every2s; success→snapshot(events with current timestamp), failure→no activity assertion. Native mode never launches or consumes historical/live log children. Explicit legacy mode is only compatibility testing, not selected by application. Restart keeps last-known state until successful current snapshot; native failure keeps it only until stale timer600s.
- Complete success snapshot updates detector active targets and marks absent active sources inactive; incomplete success delivers current positive events without marking absent sources inactive. An unreadable individual process does not suppress an independently confirmed active meeting app. Entire list failure remains unavailable; incomplete/unknown evidence without a positive target observation does not renew the600s clock. repeated active must preserve accepted/terminal consumer outcome. Inactive→active before15s grace cancels ending without new prompt.
- Bridge keeps action/id shape. List open/send/delete unchanged. Detail allows ONLY open and exact UUID match of route and current row; unsupported/unknown route, stale rows, false canOpen rejected. Main-frame/origin/session/deletion/hash fences retained.
- Native row rendering adds accessible button near existing playback; refresh removes or updates it if identity/access disappears. No paths or audio bytes sent to web. No action in ordinary browser.
- Server maps storage_capacity_exceeded to the same public reason with Russian/English quota copy; own detail has the existing billing link, shared detail has owner-contact guidance without billing. No claim of corrupt audio and no false automatic-retry promise.

Для собственной встречи сообщение о квоте содержит существующую ссылку /billing; управление объёмом сохраняет проверку billing_owner. Получатель общей встречи видит подсказку обратиться к владельцу пространства без ссылки /billing. Новые права и действия покупки не вводятся.

- Privacy Pause remains durable before source suppression. A successful Resume fixes an exact FIFO queued-frame boundary; accepted pending/queued microphone frames remain zero across Resume while subsequent frames regain normal treatment. Reads/control transitions serialize, partial reads preserve format/PTS/frame count, and suppression counts each sample once. Missing exact boundary explicitly rejects Resume and keeps paused/open checkpoint with the existing user-visible error, system capture and bounded Stop; it never waits for an empty continuously producing source.
- Playback poll binds the original meeting ID before fetch. Connected element/current main/ID are checked before recovery and after awaited recovery/text or rejection; stale responses cannot change the new route/title/body/native action/focus. Current denial still revokes its own detail.

## FR012 — атомарная граница производителя

Отдельный timestampedDiagnostics snapshot не гарантирует успешный resume. Источник должен синхронно фиксировать точный queuedFrameCount и применить callback смены подавления под той же FIFO блокировкой, что append/read. Все принятые до границы кадры остаются заглушены; новые после неё возобновляются. Default операции без гарантии возвращает отказ и callback не вызывает. Wrapper удерживает свою блокировку до FIFO операции, callback не обращается обратно к source; порядок wrapper→FIFO. Некорректная/недоступная граница сохраняет paused/open checkpoint, system audio и Stop. PTS/формат/пределы неизменны.

## FR013 — завершение без реестра

advance обрабатывает inactive/grace независимо от наличия registry; nil registry исключает новые предложения/телеметрию, но сохраняет ended для принятого события. Полный/неполный снимок, ручное подавление, отложенная Stop и600s неизвестность сохраняют прежнюю семантику.

FR014: временное auth/registry закрытие ожидающего предложения переводит только его bundleID в retryable до очистки prompt/token. Nil registry запрещает новые предложения. Восстановление и текущая активность допускают один новый Ask с прежними8s/2s. Нет prompt — accepted/terminal/manual Stop не меняются.

T016: изменившийся authEpoch в onInvalidated означает auth-driven dismissal и retryable; неизменный authEpoch сохраняет terminal. Оба порядка observers обязательны в проверке.
