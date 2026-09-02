# Contract: desktop local recording row

## Native → WebView payload

Payload — JSON array, кодированный base64 из UTF-8 bytes. WebView обязан восстановить bytes через `TextDecoder` до `JSON.parse`.

Каждая строка содержит только metadata: `id`, optional `meetingId`, `title`, `startedAt`, `durationSeconds`, `sessionDurationSeconds`, `status`, `canOpen`, `canSend`, `canDelete`, `uploadComplete`. Локальные paths и private content запрещены.

## WebView → Native action

```json
{"action":"open|send|delete","id":"opaque-item-id"}
```

- Action принимается только из main frame разрешённого desktop meeting-list route.
- Native принимает action только если текущая row projection разрешает его.
- `delete` требует подтверждения пользователя.
- `open` заново проверяет item, recordings root и существующий playback artifact.

## Handoff

- Local row отображается, пока нет пары `uploadComplete=true` + server row с тем же meeting ID.
- При выполнении обоих условий local row не создаётся.
- Server row не мутируется и не получает local ID/action.
- Следующее открытие выполняется обычным `data-meeting-open` server route.
