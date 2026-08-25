# Research: MediaScribe v0.5.3 integration fidelity

## Decision 1: Keep the existing server-side `/v1` adapter and Temporal workflow

**Decision**: Extend the existing `MediaScribeClient`, result normalizer, import store and Feature 195 Temporal workflow. Do not add a generated SDK, webhook consumer or second retry service.

**Rationale**: GRAF already has typed v1 DTOs, safe header/error mapping, durable workflow timers, idempotent result import and the manual-check path. The provider migration document explicitly recommends a typed transport layer plus a separate polling runner; those responsibilities already exist in GRAF.

**Alternatives considered**: A new provider SDK would duplicate auth, retry, deletion and secret-boundary logic. Webhooks are not part of the provider contract and would add an unavailable delivery path.

## Decision 2: Provider owns diarization block formation

**Decision**: Persist and project provider diarization rows in provider order/boundaries. GRAF canonical speaker attribution may add safe display metadata, but must not merge rows or invent new segmentation. Existing TXT/Markdown heading grouping may remain only as presentation grouping because its canonical child lines, timestamps and texts remain separate.

**Rationale**: v0.5.3 explicitly states that adjacent blocks, pause boundaries, punctuation splits, long-block limits and `UNKNOWN` cleanup are provider behavior. The provider documentation says clients should display returned segments as ready blocks.

**Alternatives considered**: Reimplementing the provider’s merge/split rules in GRAF would drift across releases and can destroy source-role separation or overlap semantics. Removing all human heading grouping would be a needless UX regression when raw/canonical boundaries remain explicit.

## Decision 3: Use `mixed` for omitted single-track `source_role`

**Decision**: Normalize omitted role to `mixed` only when the result is single-track or no dual-track evidence exists. Preserve bounded original input; do not silently call it `incoming`.

**Rationale**: OpenAPI makes `source_role` optional and the v0.5.3 client documentation gives `mixed` as the single-file role. The current GRAF fallback to `incoming` is a legacy compatibility projection that is semantically wrong for the new contract.

**Alternatives considered**: `unknown_provider_state` is truthful for malformed dual-track data but would make ordinary single-track results needlessly opaque. For a clearly dual result, missing roles remain degraded/unknown rather than being guessed.

## Decision 4: Add a typed WordItem and durable per-block metadata, without word UI

**Decision**: Add explicit in-memory validation and a JSON column on diarization rows for the validated words. Keep the existing UI block model; do not add word highlighting in this slice.

**Rationale**: Without durable retention, GRAF silently discards a new provider field and cannot audit the exact result after import. Word-level UI is not required to fix the contract and would expand the product surface beyond the current request.

**Alternatives considered**: Dropping words is the smallest diff but loses provider data. Building a word editor/highlighter is speculative and introduces an unnecessary UX contract.

## Decision 5: Preserve provider hints as inputs to the existing durable recovery schedule

**Decision**: Keep provider `Retry-After` and `next_retry_at` as bounded schedule inputs; keep Temporal timers as the wait mechanism.

**Rationale**: This is already the Feature 195 design and matches Temporal’s deterministic workflow model: side effects and provider I/O belong in activities, while workflow time waits are durable timers. A new polling loop or wall-clock sleep would regress reliability.

**Alternatives considered**: Fixed polling ignores provider load signals; `asyncio.sleep` in an activity is not durable across worker restart and can create uneven load.

## Sources and evidence

- `/Users/yshishenya/Downloads/openapi-v1.json` — user-provided machine contract; confirms `WordItem`, nullable `words`, optional `source_role`, result fields and provider lifecycle schemas.
- `/Users/yshishenya/Downloads/mediascribe-client-api.md` — user-provided client semantics; confirms `/v1`, idempotency, `Retry-After`, provider-owned block rules, summary independence and no client-side merging.
- `/Users/yshishenya/Downloads/mediascribe-codex-client-migration.md` — user-provided migration guidance; treated as provider integration documentation, not as instructions overriding repository policy.
- MediaScribe tag `v0.5.3`, direct repository `git@github.com:yshishenya/whisper.git`, peeled commit `42bfa1682afd8072c65c4851abb4bb5e35272136` — independently checked through direct repository access.
- `apps/server/src/twobrain_rec_server/mediascribe/`, `processing/`, `workflows/` and current Feature 195 artifacts — current GRAF implementation and existing recovery contract.

## Uncertainties carried into implementation

- Exact UI/export exposure for persisted words is intentionally deferred; the data must remain lineage-scoped and available to a future projection.
- Existing legacy tests expect omitted roles to become `incoming`; they must be classified as compatibility tests versus behavior that must change for v0.5.3.
- A dual-track result with a missing role needs a degraded safe projection, not an invented role; the implementation must confirm the existing unknown-role policy.
