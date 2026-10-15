# Calendar series view contract

GET `/api/v1/calendar/series/{series_key}/occurrences`

Optional `view`: all (default, unchanged), upcoming, history. Existing from/to/limit1..50/cursor rules unchanged. New view cursor includes immutable view+anchor; forbidden view/cursor mismatch422. Existing all cursor remains valid until existing expiry. Upcoming orders (starts_at,id) ASC; history DESC; ongoing is upcoming until ends_at<=anchor. Cancellation visible with no Join; ACL/deletion/privacy run each page. Private timestamps never emitted when preference masks time. JSON Cache-Control no-store.

New `temporal_state` enum upcoming/ongoing/history on each projection. Other fields unchanged. Existing clients ignore additive field. No mutation, recording start, notification setting or provider call.

UI contract: native details; named button group with two aria-pressed controls; scope hint; article rows; polite status; retry/more button; one help details. Expanded rows retain per-event Join UUID; recordings use authorised UUID paths only. Status/empty/reset and no-late-response rules are FR-006. Native and browser Join resolver security remain unmodified.
