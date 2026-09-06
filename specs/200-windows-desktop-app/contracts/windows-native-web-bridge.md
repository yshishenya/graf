# Contract: Windows WebView2 navigation and native bridge

Дата: 2026-09-06

## 1. Trusted origin

The production origin is the normalized HTTPS origin configured by the same
cabinet configuration as macOS. The packaged default is:

```text
https://rec.2brain.pro
```

Allowed paths are the existing server-owned desktop route kinds, including:

- `/desktop/meetings`;
- `/desktop/meetings/{meeting_id}`;
- approved meeting share/deletion-report routes;
- approved `/desktop/settings/...` and auth recovery routes already accepted by
  the cabinet route policy.

The implementation must port the existing exact route-kind decision model. It
must not use a broad `contains("desktop")` or `contains("meeting")` check.

Unknown scheme/host/port, `file:`, `data:`, `javascript:`, local filesystem,
loopback not explicitly enabled for local development, downloads requiring native
file access and native-only capture routes are denied or opened externally by a
bounded policy.

## 2. WebView2 settings

For the remote cabinet:

- use WebView2 Evergreen Runtime and check runtime availability before creating
  the control;
- set `AreHostObjectsAllowed = false`;
- enable web messages only when the specific bridge is configured;
- do not expose COM host objects, arbitrary native methods or filesystem APIs;
- disable default script dialogs and unneeded capabilities;
- keep host process standard-user/non-elevated;
- remove or invalidate bridge state when the document/session boundary changes.

## 3. Envelope

Every web-to-native request uses:

```json
{
  "protocol": "graf.desktop.bridge",
  "version": 1,
  "direction": "web_to_native",
  "message_id": 1,
  "nonce": "ephemeral-nonce",
  "origin": "https://rec.2brain.pro",
  "command": "request_app_quit",
  "payload": {"action": "quit"},
  "sent_at_monotonic_ms": 12345
}
```

Limits for the first version:

- maximum serialized message: 64 KiB;
- maximum payload nesting: 8 levels;
- `message_id` is a positive monotonically increasing unsigned integer per
  WebView document; `nonce` is rotated at every successful document boundary;
- command strings and bounded payload strings have explicit allowlists/limits;
- no arrays of audio samples, file paths, cookies, tokens or transcript text;
- one in-memory nonce per WebView session, rotated on navigation/auth boundary.

Native rejects malformed JSON, unknown version/command, wrong direction, invalid
nonce, duplicate/expired message id, unapproved source or oversized payload
without a local side effect.

## 4. Native-to-web events

### `native_ready`

The native host sends the envelope from section 3 with direction
`native_to_web`, command `native_ready`, message id `1` and an empty payload.
It supplies the current document nonce after the typed bridge script is ready.
This is initialization, not authority to record, upload or delete. No
acknowledgement command is accepted from the web page.

### `local_recordings`

The native host sends `{"command":"local_recordings","nonce":"...","rows":[]}`
only to the current approved document. This bounded display message is distinct
from the web-to-native request envelope; it grants no native authority. The
page passes the rows to `window.GRAFLocalRecordings.update(rows)` as described
in section 8. Paths, credentials and recording contents are excluded.

Capture, readiness, runtime recovery and aggregate custody state are displayed
by native controls. The earlier proposed `capture_state`, `custody_summary`
and `runtime_state` messages are not part of the active protocol.

## 5. Web-to-native intents

The initial allowlist is intentionally small:

| Type | Effect | Allowed while capture active |
|---|---|---:|
| `request_app_quit` | validate exact `{"action":"quit"}`; stop active capture and wait for native finalization before closing | yes, close waits for finalization |
| `local_recording` | validate exact `{"action":"open\|send\|delete","id":"known-local-id"}` and the current row capability; see section 8 | only when current native state permits that action; deletion is blocked during capture/upload |

No compatibility aliases are accepted. `open_native_settings`,
`request_native_settings`, `open_native_diagnostics`, `request_diagnostics`,
`request_runtime_repair`, `ack` and `ack_display` are rejected. Settings,
diagnostics and runtime recovery remain available through native controls and
approved navigation, not dormant bridge handlers.

`start_recording`, `stop_recording`, `pause_recording`, `resume_recording`,
`read_file`, `write_file`, `run_process`, `set_audio_device`, `get_token`,
`get_cookie` and generic method names are rejected. User control remains native.

## 6. Navigation lifecycle

1. On `NavigationStarting`, normalize and evaluate origin/route before allow.
2. On accepted new document, create a fresh nonce and clear old bridge state.
3. On `ContentLoading`/document-created, do not inject a generic privileged
   script; only the reviewed typed quit/local-recording bootstrap for the exact
   trusted origin may be installed.
4. On auth expiry, route block, WebView recreation or origin change, invalidate
   nonce and stop sending sensitive state.
5. On `WebMessageReceived`, compare the message source with the current WebView
   source/origin, then parse and validate the typed envelope.
6. On runtime or network error, leave native capture/custody state untouched and
   show bounded UI outside the document.

## 7. Security tests

The contract is not complete until tests cover:

- untrusted origin posting a valid-looking message;
- trusted origin with stale nonce;
- malformed JSON and unknown type/version;
- oversized/deep payload;
- replayed message id;
- attempted native control/file/token commands;
- non-quit app-close payloads and quit requests from a non-approved route;
- cross-frame/redirect navigation;
- WebView close/recreate during active recording;
- missing runtime and runtime repair failure.

## 8. Локальные записи: уточнение паритета от 2026-09-06 (T083/T084)

Windows использует существующий `window.GRAFLocalRecordings.update(rows)`
кабинета, как macOS. В веб передаются только строки для отображения: непрозрачный
локальный `id`, фиксированное название записи, время и длительность при наличии,
состояние, флаги `canOpen`, `canSend`, `canDelete`, `uploadComplete`. Пути,
учётные данные и содержимое записи в строки не входят. Нет достоверной даты —
показывается «На этом компьютере», дата не выдумывается.

Единственный новый запрос `local_recording` имеет ровно два строковых поля:
`{"action":"open|send|delete","id":"known-local-id"}`. Проверяются текущий
документ/nonce, типы, точные поля, ограничения длины, принадлежность id последнему
нативному списку и разрешение действия. Перед эффектом нативный владелец повторно
проверяет актуальное состояние записи и границы хранилища. Запрос не является
доступом к произвольным файлам и не может выбирать путь.

`open` открывает только проверенный готовый файл прослушивания; повреждённая или
ещё активная запись не объявляется доступной. `send` запускает существующую
очередь без повторной отправки завершённого пакета. При отсутствии входа
открывается вход с возвратом в список. `delete` требует отдельного нативного
подтверждения конкретной записи; запись/отправка в процессе блокирует удаление.
Это удаление локальной копии по явному решению пользователя, не серверная команда
удаления и не подтверждение серверной очистки. Команды очистки сервера остаются
закрытым условием до появления достоверной авторизации конкретной установки.

Проверки: неизвестный id, подмена действия/лишние поля, смена документа,
повтор сообщения, устаревшие разрешения, активная запись/отправка, отмена
подтверждения, ошибка хранилища. Ни одна ошибка не выдаётся за успешное удаление.
