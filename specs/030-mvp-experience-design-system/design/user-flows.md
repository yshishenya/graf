# User Flows

## Record In App

Desktop ready -> active recording -> Stop -> local saved -> queued/uploading
-> uploaded -> audio extraction if needed -> transcription -> transcript ready
-> notes ready -> meeting review complete -> deletion/access entry.

## Upload Owned Media

Web or embedded `Добавить запись` / `Загрузить медиа` -> shared server-owned
upload sheet over the meeting workspace -> accepted media category -> metadata
-> inline validation -> `Начать загрузку` -> list row appears or updates ->
upload progress -> audio extraction -> transcription -> transcript ready ->
notes ready -> meeting review.

Unsupported/no-audio path:

Upload -> validation failure -> explain what failed -> upload another file or
cancel.

## Search And Filters

Meetings list -> search field or search navigation -> contextual command overlay
over the same list -> search by title, participant, status, or transcript phrase
-> open result to meeting detail or apply filters -> return to the meetings
list.

Search/filter are list-level layers. They are not standalone MVP destinations
and should not create separate native desktop logic.

## Degraded Processing

Uploaded -> transcription or notes failure -> partial/degraded review -> show what exists -> retry/support/continue reviewing available outputs.

## Browser Handoff

Embedded cabinet route -> route matrix checks browser-only -> desktop explains reason -> browser cabinet opens route.

Examples:

- Share access level change.
- Public link.
- Billing/team/admin.
- Transcript regeneration.
- Delete/deletion report.
- Download/export management.

## AI Scope

Meeting review -> AI drawer -> scope defaults to this meeting -> all-meetings
scope is browser/deferred until privacy/search policy is specified.

## Speaker Assignment In Desktop

Desktop meeting review -> `Спикеры` -> embedded server-owned speaker assignment
route -> rename/merge/assign speaker -> save to server -> desktop review shows
updated labels from the same backend state.

Native macOS owns only the window host and capture strip during this flow. The
speaker data, segment evidence, save state, conflicts, and retry behavior come
from the web/backend surface so Windows and Linux shells can reuse the same
product UI.

## Deletion/Access

Meeting review -> deletion/access entry -> bounded deletion/access state -> dependency truth where relevant.
