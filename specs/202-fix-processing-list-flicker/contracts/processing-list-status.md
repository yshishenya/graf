# UI Contract: Processing status in meeting list

1. A row is eligible for client projection only when its current server status
   kind is `processing`.
2. Projection identity and current list generation must match before mutation.
3. The readiness node exists in initial server HTML for an eligible row.
4. Intermediate projection replaces only that node's text/data attributes.
5. Failed/blocked/terminal rows are never eligible, regardless of API payload.
6. A terminal processing state requests one canonical list refresh; it is not
   rendered as a competing client terminal status.
7. Authoritative user requests cancel projection requests/timers and retain
   current focus/selection recovery behavior.
8. Upload/playback progress swaps may replace the list, but must synchronously
   restore the last matching non-terminal processing projection and retain its
   15-second request throttle.
