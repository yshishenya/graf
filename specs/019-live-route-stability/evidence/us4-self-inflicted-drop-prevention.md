# US4 Self-Inflicted Drop Prevention Evidence

US4 evidence must prove that idle timers, housekeeping, stale cached state, and false silence classification cannot release a healthy active route.

Required metadata-only facts:

- release decision event and route session id
- client activity snapshot used for the decision
- outcome: keep_active, denied, or released
- reason: denied_active_client, denied_ambiguous_evidence, denied_stale_evidence, or meeting_client_closed
- preserved/stale/released/blocked/failed route truth after app restart simulation
- regression result for the observed 300-tick idle release pattern
