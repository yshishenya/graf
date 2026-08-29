# Outcome lifecycle contract

## Initial result

1. A usable transcript creates/reuses one `automatic_baseline` AI candidate.
2. UI shows preparing/blocked/failed truth while no accepted result exists.
3. Strict schema, category parity, exact source reference and trust validation run before storage.
4. The first valid AI result is shown as a ready candidate and is accepted only after explicit user action while source/deletion/access and expected-current fences match.
5. Deterministic extraction never becomes ready accepted content for a new revision-scoped meeting.

## Manual format and refresh

1. Selection creates/reuses a candidate bound to exact source/template/prompt lineage.
2. Current accepted result remains visible and is the only share/export truth.
3. Ready candidate is previewed.
4. User chooses `Использовать`, closes comparison, explicitly rejects or selects another format.
5. Acceptance is atomic against expected current accepted pointer.

## Failure semantics

- dependency wait: bounded pending state;
- temporary provider/prompt/transport failure: retry or refresh status;
- invalid model result: candidate rejected/failed, accepted result unchanged;
- source/template/access/deletion change: stale/blocked and cannot accept;
- ambiguous provider boundary: never repeat inference automatically.

## Idempotency

Repeated automatic requests and repeated manual intent IDs return/reconcile the same logical candidate. A deliberate new manual refresh uses a new intent ID.
