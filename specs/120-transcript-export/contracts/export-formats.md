# Contract: Export Format Projections

Every projection consumes one frozen `ExportSnapshot`. Filenames are stable,
sanitized, collision-safe, and identify meeting/content scope/revision without
embedding private content. UTF-8 is used for every text format.

## Shared invariants

- Raw source rows remain complete in JSON; all other formats use ordered
  canonical turns unless explicitly described as human display groups.
- No format inserts `Пауза`, `[pause]`, ellipses for silence, or any fabricated
  speech row/cue.
- Machine rows never merge on display label. Stable key, attribution, source
  role, result, overlap, invalid timing, and gap boundaries are preserved.
- Unknown/unconfirmed attribution is explicit and never confirmed as
  `SPEAKER_00`.
- Missing summary sections, owners, due dates, or evidence are explicit/empty;
  values are never invented.
- Untrusted content cannot become Markdown/HTML markup, CSV/XLSX formulas,
  external links, macros, or subtitle styling.

## TXT

- Optional UTF-8 BOM is not required; use UTF-8 bytes and platform-neutral `\n`.
- Header: title, content scope, saved revision/status, language, duration.
- Transcript: readable speaker blocks; each canonical child turn retains its
  timestamp. Short adjacent groups are presentation-only.
- Summary: ordered category headings and item states; owner/due date/evidence
  only when stored.
- Combined: explicit `Транскрипт` and `Саммари` boundaries.

## Markdown

- CommonMark-compatible headings/lists with escaped untrusted punctuation.
- No raw HTML generated from meeting content and no provider/storage links.
- Transcript and summary structure mirrors TXT; evidence uses safe timestamp
  labels/turn ids, not unauthorized playback URLs.

## CSV

One canonical turn per row, stable header order:

```text
sequence,turn_id,start_ms,end_ms,start_time,end_time,speaker_key,speaker_label,
attribution_state,source_role,text,overlap,source_segment_ids,
processing_result_id,turn_policy_version
```

- RFC-style comma delimiter, double-quote escaping, CRLF rows, UTF-8 BOM.
- `source_segment_ids` is a stable JSON array string.
- Untrusted string cells beginning with formula-trigger characters are written
  as inert text while preserving visible content.
- CSV is transcript-only; it never smuggles summary rows into the same schema.

## XLSX

MIME:
`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`.

Fixed sheet names/order:

1. `Transcript`: same canonical columns as CSV; frozen header, filter, wrapped
   text, safe widths, typed integer/boolean cells.
2. `Summary`: category, sequence, state, text, truth label, evidence turn ids,
   resolved source references, and unresolved references.
3. `Action Items`: sequence, state, text, owner, due date, truth label,
   evidence turn ids, resolved source references, and unresolved references.
4. `Metadata`: schema/renderer/turn-policy versions, meeting/result/outcome
   revision, summary revision token/source/generator/category states, content
   scope, language, duration, and stored status.

All sheets exist so workbook structure is stable. Unselected/unavailable
content uses a metadata/status row, not invented content. Untrusted values are
literal strings; workbook contains no formula, macro, external link, image, or
embedded audio.
When evidence is deselected, all three evidence/reference columns remain in the
stable schema but contain empty JSON arrays.

## JSON

MIME: `application/json; charset=utf-8`.

Top-level envelope:

```json
{
  "schema_version": "graf.transcript-export.v1",
  "renderer_version": "export-v1",
  "meeting": {},
  "selection": {},
  "revisions": {},
  "transcript": {
    "status": "ready",
    "raw_segments": [],
    "canonical_turns": []
  },
  "summary": null,
  "provenance": {}
}
```

- Object keys are serialized deterministically; arrays remain canonical order.
- Times are integer milliseconds plus optional human labels.
- Raw segments preserve content/order/timing/source refs and safe provider-
  neutral provenance, including explicit invalid/source-only rows.
- Canonical turns contain stable identity, attribution, boundaries, and raw ids.
- Summary contains saved revision/status/category items and resolved/unresolved
  evidence references.
- Exclude credentials, tokens, signed URLs, object keys, provider job secrets,
  raw audio, audit actor data, request ids, and delivery timestamps from the
  canonical envelope.

## SRT

One eligible canonical turn per cue:

```text
1
00:00:00,000 --> 00:00:01,250
Спикер: Текст

```

- Counter begins at 1 and is consecutive.
- Times use `HH:MM:SS,mmm`; hours do not wrap at 60 minutes.
- Valid overlap is preserved; cues are never shifted to hide it.
- Invalid/empty raw rows remain explicit in JSON with their omission state but
  do not become an invalid cue.
- Strip/control newline structure and make HTML-like text literal; no styling
  tags are generated.
- Speaker prefix follows the selected option but unknown remains explicit.
- SRT is transcript-only and contains no summary or synthetic silence cue.

## Determinism

For the same snapshot and selection, TXT/MD/CSV/JSON/SRT bytes are identical.
XLSX semantic cell/sheet content is identical; package metadata that the writer
cannot make byte-stable is explicitly excluded from canonical comparison and
validated by parsing. Filename, MIME, sheet/column order, JSON schema, and
renderer version remain stable.
