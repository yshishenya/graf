# US3 Recording Timeline Evidence

US3 evidence must show that local microphone and incoming tracks remain aligned during accepted recordings and are truthfully categorized when route continuity is lost.

Required metadata-only facts:

- recording session id and route session id
- optional autorepair attempt ids correlated with recording timeline
- mic and incoming durations and computed duration difference
- alignment band: accepted, degraded_warning, or failed
- route interruption category
- manifest status and transcription readiness

Accepted runs require `durationDifferenceSeconds <= 3`. Degraded and failed runs remain useful diagnostic evidence but do not count as acceptance.
