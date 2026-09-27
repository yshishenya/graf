# F277 — Состояние уведомлений

## Durable recording start acceptance (расширение 2026-09-27)

`LocalRecordingManifest.startAcceptance: LocalRecordingStartAcceptance?`:
`pending` → `accepted` только для той же активной сессии после проверки
актуальности. nil — старый пакет, прежние проверки; неизвестный enum — ошибка
чтения, не разрешение. Новые manual starts сохраняют accepted, новые
meeting-detection starts — pending. До accepted сохранённый scopeApproval=nil;
исходное разрешение хранится в writer memory и сохраняется только вместе с
accepted. Ошибка подтверждения не меняет память и pending на диске. Stop и
recovery сохраняют признак; pending никогда не считается upload-eligible.
Поле локальное, без частных данных; новые серверные поля не вводятся.

## Preferences

Owner-scoped `reminders: Bool=true`, `offsetMinutes: Int=1` (0/1/5), `showTitles: Bool=false`, `sound: Bool=false`; добавить `quiet: Bool=false`. Decoder отсутствующего quiet использует false, сохраняя остальные старые значения. Offset валидируется. До доверенного owner не сохранять; ошибку записи не объявлять успехом.

## Content and lifecycle

Пять semantic variants: meeting, recordingPrompt, problem, shortRecording, preview. Optional title/detail/icon/checkbox/ordered actions. Prompt хранит remainingSeconds/rememberChoice без progress. Domain decision вне view.

Envelope: context generation, event identity, content, absolute deadline, terminal flag. Meeting identity включает eventID/start; context — account/workspace/serverorigin. Incident identity — запись/incident kind без названия. Preview не доменное событие.

States: pending→visible→acted/dismissed/expired/invalidated. Один terminal переход; callback прежней generation/послеterminal — no-op. Tick/check не создаёт envelope/deadline. Prompt защищён; прочие pending вычисляются из ограниченного актуального snapshot, не бесконечногоFIFO. После prompt заново выбрать актуальное событие. Dismiss запоминает identity в окне актуальности, не исправляет underlying error.

Meeting due=startsAt-offsetMinutes×60; deadline=min(due+120s,endsAt). Offset0 допускает карточку после начала в этом окне. Перенос/удаление/изменение ссылки/начало записи инвалидируют старые actions. Wake не показывает просроченное.

## History

До50entries newestfirst в памяти: UUID, Date, closed enum kind, нейтральный текст из enum. Без meetingname/sessionpath/URL/participant/transcript/audio/replayaction. Short/problem добавляются даже в quiet; preview/tick нет. Тот же incident не дублируется; новое возникновение после resolution допускается. Contextreset очищает history/card. Проблема остаётся в existing recordingstatus.

## Retirement

UserNotifications ограничен helper очистки own pending/delivered, без отправки/authorization. Cleanup идемпотентен при каждом запуске: повторно удаляет собственные системные запросы без сохранения старого канала доставки. Перенос claims односторонний; точная дедупликация после повторного запуска старой версии и её новых записей не заявляется. Старые claims удалить либо перевести в currentincidentidentity для дедупликации; никаких двусторонних aliases. Session ownership сохраняется как действующая privacy boundary.
