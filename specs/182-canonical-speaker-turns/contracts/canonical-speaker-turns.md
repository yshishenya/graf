# Contract: Canonical Speaker Turns

## Accepted result

For a contract-valid provider result:

- each non-empty provider speaker row produces exactly one canonical source
  turn before adjacent same-identity presentation grouping;
- start/end, raw provider key, text, and order come from that row;
- the stable speaker key is independent of display order;
- `transcript[]` remains separately available as unattributed evidence;
- no ASR-to-speaker winner is computed.

## Degraded result

If provider attribution is unsafe:

- result state is `degraded_provider_result`;
- canonical display contains valid non-empty ASR evidence exactly once;
- attribution is `mixed` or `uncertain` and has no provider identity;
- unsafe provider-row text is not emitted;
- review, timeline, exports, and outcomes expose the same state and order.

If the only defect is a tiny explicit unknown identity:

- result state is `degraded_provider_result`;
- the unknown row remains visible once with `unknown` attribution and the
  display label `Спикер не определён`;
- other contract-valid provider rows remain confirmed;
- the unknown row is excluded from participant count and rename.

## Identity

- `provider_speaker_key` preserves the received key.
- `speaker_key` is stable for the same processing result and provider key.
- `canonical_label` may change with display order without changing identity.
- unknown/mixed/uncertain keys are not confirmed participants and cannot be
  renamed.
- legacy ordinal names are used only under provable one-to-one compatibility.

## Time

Canonical values retain database Decimal precision. Renderers may round a copy
for presentation; rounded values never feed ordering, identity, merging, or
another consumer.

## Consumer parity

The ordered tuple `(start, end, speaker_key, provider_speaker_key, text,
attribution_state, result_state)` is authoritative for API transcript, timeline,
Markdown, CSV, XLSX, JSON, SRT, VTT, and downstream outcomes.
