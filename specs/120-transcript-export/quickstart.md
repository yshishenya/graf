# Quickstart: Canonical Transcript And Summary Export

## Prerequisites

- Work from branch `120-transcript-export`.
- Use synthetic meeting text, ids, and metadata only.
- Do not use production credentials, signed URLs, provider payloads, real audio,
  private transcripts, or screenshots containing meeting content.
- Start the server test environment using the existing repository workflow.

## Canonical fixture matrix

Create one deterministic fixture set whose expected result is shared by all
serializers.

| Case | Input | Required result |
|---|---|---|
| short gap | same confirmed key/role/result, 0.9 s | one canonical turn under inclusive 1.0 s rule |
| exact threshold | same confirmed key/role/result, 1.0 s | one canonical turn |
| over threshold | same confirmed key/role/result, 1.1 s | two turns; no pause row/text |
| medium/long gaps | 3 s, 51 s, 138 s | separate turns/groups; timestamps expose the jump; no fabricated speech |
| speaker return | A → B → A | three ordered turns/groups; A is not continuous |
| unknown | no confirmed mapping / `UNKNOWN` | explicit unknown singleton; never confirmed `SPEAKER_00` |
| same visible label | distinct stable speaker keys | never merged |
| source boundary | incoming → microphone or other role | never merged |
| result boundary | adjacent rows from different revisions | rejected from one snapshot; never merged |
| overlap | valid overlapping A/B turns | preserve overlap in structured rows/SRT; no silent shift |
| invalid timing | negative/end-before-start | raw JSON retains safe state; no merge evidence or SRT cue |
| empty row | whitespace text with source identity | raw JSON retains state; no fake turn |
| partial | non-terminal result | canonical export disabled with truthful reason |
| missing summary | broad status says available but no stored outcome content | summary/combined disabled; transcript remains independent |
| long duration | turn after 01:00:00 | human/SRT time does not wrap at 59:59 |
| Russian/hostile text | commas, quotes, CR/LF, Markdown/HTML punctuation, `=+-@` prefixes | visible text preserved and inert in every format |
| policy/access | owner, permitted viewer, view-only export-disabled, denied | only current allowed scope returns bytes |
| deletion | deletion starts before request or while preparing | no bytes; safe lifecycle reason/audit |
| audit failure | requested/completion audit write fails | fail closed; no bytes |
| revision race | newer result/outcome appears after snapshot | output stays on requested pins; no mixed revision |
| provider swap | equivalent canonical inputs from second adapter | semantically identical projections |

## Focused automated checks

After implementation, run:

```sh
uv run --project apps/server --extra dev pytest -q \
  apps/server/tests/unit/test_transcript_exports.py \
  apps/server/tests/unit/test_cabinet_view_models.py \
  apps/server/tests/contract/test_transcript_export_contract.py \
  apps/server/tests/contract/test_transcript_export_no_secret_egress.py

bash apps/server/scripts/run_local_postgres_tests.sh --focused -q \
  tests/integration/test_transcript_export_egress.py \
  tests/integration/test_cabinet_meeting_detail.py \
  tests/integration/test_rls_postgres_policies.py::test_content_export_sources_and_audit_sink_are_tenant_isolated
```

Expected:

- all fixture cases pass from one snapshot;
- raw/plain download compatibility tests still pass;
- no content/secret fields appear in problem, audit, or activity payloads;
- denied/deleted/audit-unavailable paths return no attachment body.

## Cross-format semantic comparison

For each transcript fixture:

1. Build one frozen snapshot.
2. Export all six formats without rebuilding the snapshot.
3. Parse CSV with Python `csv`, JSON with `json`, and XLSX with `openpyxl`.
4. Parse SRT blocks using the strict fixture helper.
5. Assert order, text, start/end, speaker key/label/state, source role, source
   ids, selected result, and renderer/schema versions match the snapshot.
6. Assert TXT/MD contain every canonical child timestamp and no pause marker.

Repeated text exports must be byte-identical. XLSX must be semantically
identical after parsing; writer-owned ZIP metadata is excluded only when
documented by the test.

## Format safety checks

- CSV round-trips quotes, comma, CR/LF, Russian text, and formula prefixes as
  inert visible text.
- Markdown renders punctuation/HTML-like text literally and introduces no raw
  HTML, link, or executable construct from meeting content.
- XLSX has exactly `Transcript`, `Summary`, `Action Items`, and `Metadata`, no
  formula/macro/external link, and all untrusted values have string cell type.
- JSON rejects non-finite numbers and contains no credential, job, path, URL,
  audit actor, or delivery-only field.
- SRT uses consecutive cues, millisecond comma syntax, no hour wrap, no pause
  cue, and no timing shift for overlap.

## Policy, lifecycle, and revision checks

- Exercise transcript-only, summary-only, and combined permissions separately.
- Revoke access between capability read and POST; POST must re-check and deny.
- Start deletion before POST and during a held export transaction; no bytes may
  escape after lifecycle denial.
- Force requested and completion audit failures; both fail closed.
- Request old/stale result and outcome-set ids; receive safe revision error.
- Insert a newer result/outcome after snapshot creation; exported metadata and
  content remain entirely on the pinned snapshot.
- Inspect activity/audit rows: metadata only, correct outcome/format/scope/ids,
  no source text or speaker display name.

## UI, accessibility, and IA review

Using synthetic content in the in-app browser and embedded-width surface:

1. Open meeting detail and confirm one contextual `Экспорт` action plus one
   Files/governance availability state.
2. Confirm scope-first selection and only compatible grouped formats.
3. Confirm revision/readiness/language/duration/options and structural preview.
4. Submit each format and observe immediate announced preparing state, duplicate
   submit prevention, correct filename/MIME/length, and focus return.
5. Trigger partial, missing summary, denied, deletion, generation failure, and
   audit-unavailable states; confirm safe distinct reasons and retry behavior.
6. Complete the dialog using keyboard only; test Escape/close, focus trap and
   return, visible focus, screen-reader names/live status, reduced motion,
   non-color meaning, 200% zoom, mobile width, and desktop embedded width.
7. Check console errors, horizontal overflow, and that no competitor assets,
   labels, layout, colors, or icons were copied.

## Performance checks

Use synthetic 60-minute and greater-than-one-hour fixtures:

- TXT/MD/CSV/JSON/SRT attachment ready within five seconds.
- XLSX/combined UI progress visible within one second and response completes
  within thirty seconds.
- Snapshot and text serializers stay linear in rows/items.
- Record timings/counts only; never record meeting text or raw source payloads.

If XLSX exceeds the supported budget, stop implementation closeout and propose a
separate short-lived artifact slice. Do not silently add a table, worker, or
storage lifecycle inside feature 120.

## Repository gate

```sh
git diff --check
cd apps/server && uv run --extra dev ruff check src tests
cd ../..
infra/scripts/ci-local.sh
```

Production deploy, provider migration, destructive deletion, and release
mutation are not part of this quickstart.
