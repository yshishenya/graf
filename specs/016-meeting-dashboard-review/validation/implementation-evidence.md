# Implementation Evidence: Meeting Dashboard Review

Feature: `016-meeting-dashboard-review`
Date: 2026-06-16

## Story Checkpoints

- US1 authorized list: implemented through `GET /api/v1/cabinet/meetings`
  and `/meetings`. Focused tests verify workspace scoping, search, status
  filter, sort, limit, dense reference-informed list controls, and no transcript
  or dependency identifier egress from list responses.
- US2 ready detail: implemented through `GET /api/v1/cabinet/meetings/{id}`
  and `/meetings/{id}`. Focused tests verify ordered transcript segments,
  timestamp labels, source-role truth, speaker lanes, playback shell, and
  notes-unavailable truth for 016.
- US3 processing/degraded states: implemented for processing, failed, partial,
  empty transcript, and foreign meeting denial. Focused tests verify no fake
  transcript, no generated notes, safe reasons, safe next actions, and
  privacy-preserving 404 for foreign meetings.
- US4 governance slots: implemented as stable non-mutating states for share,
  export, download, retention, deletion, assistant, template, star, tag, access,
  and more. Delete copy is bounded to data 2brain Rec controls.
- US5 desktop embedded routes: implemented at `/desktop/meetings` and
  `/desktop/meetings/{id}`. Focused tests verify embedded pages exclude native
  capture, screen recording, device, noise/accent, local path, and diagnostics
  controls.

## Validation Commands

Focused cabinet suite:

```sh
cd apps/server
uv run --extra dev pytest -q --tb=short \
  tests/contract/test_cabinet_contract.py \
  tests/contract/test_cabinet_no_secret_content_egress.py \
  tests/integration/test_cabinet_meeting_list.py \
  tests/integration/test_cabinet_meeting_detail.py \
  tests/unit/test_cabinet_view_models.py \
  tests/unit/test_cabinet_web_shell.py
```

Result: `23 passed in 5.43s`.

Full server pytest and Ruff after final UI changes:

```sh
cd apps/server
uv run --extra dev pytest -q && uv run --extra dev ruff check .
```

Result: `360 passed, 4 skipped in 25.95s` and `All checks passed!`.

## Screenshots

Sanitized screenshots were generated from local `TestClient` seeded data and
captured with headless Chrome. The raw authenticated Krisp references remain
outside the repository and are not committed.

- `specs/016-meeting-dashboard-review/validation/screenshots/01-list.png`
  - Browser list at 1440x900.
  - Shows left rail, upcoming meetings, dense meeting rows, status chips,
    filter/sort/search affordances, `New`, upload placeholder, row future
    slots, and floating assistant entry.
- `specs/016-meeting-dashboard-review/validation/screenshots/02-ready-detail.png`
  - Ready detail at 1440x900.
  - Shows breadcrumb/actions, `Notes` plus `Recording & Transcript`, safe
    transcript segments, speaker lanes, governance placeholders, assistant and
    template slots, and playback bar.
- `specs/016-meeting-dashboard-review/validation/screenshots/03-processing-detail.png`
  - Processing detail at 1440x900.
  - Shows truthful waiting state and no fake transcript, notes, share success,
    export success, or delete success.
- `specs/016-meeting-dashboard-review/validation/screenshots/04-desktop-embedded-detail.png`
  - Desktop-embedded route at 1440x900.
  - Shows the same web-owned review surface without sidebar or native capture
    controls.
- `specs/016-meeting-dashboard-review/validation/screenshots/05-mobile-list.png`
  - Browser list at 390x844.
  - Confirms top actions wrap, rows stay scannable, and the assistant input no
    longer overlays list content.
- `specs/016-meeting-dashboard-review/validation/screenshots/06-mobile-ready-detail.png`
  - Ready detail at 390x844.
  - Confirms transcript segments stack, long copy wraps, right panel stacks, and
    playback stays anchored without hiding visible content.

## Reference Comparison

- V8 and Krisp reference direction: post-meeting review is a dense work surface,
  not a landing page. The implemented first screen opens directly into
  meetings and status rows.
- Krisp web/desktop pattern: the post-meeting product surface is web-owned and
  can be embedded in desktop. The implemented `/desktop/meetings` routes reuse
  server-owned review UI and intentionally omit native capture controls.
- Meeting list pattern: upcoming meetings, meeting-note rows, search/filter/sort
  affordances, row hover/future slots, and `New`/upload placement are reserved
  without implementing out-of-scope capture or upload behavior in 016.
- Ready detail pattern: `Notes` and `Recording & Transcript` information
  architecture, transcript timestamps, speaker labels, speaker distribution,
  governance actions, assistant/template slots, and playback shell are present.
- Processing pattern: pending detail remains useful and truthful while content
  is unavailable. It does not fabricate transcript, notes, or AI output.
- Governance boundary: share, export, download, retention, deletion, assistant,
  template, tags, and access affordances are visible in stable locations but
  remain non-mutating until later feature slices own policy, audit, and egress.

## Accessibility, Responsive, And Layout Checks

- Keyboard focus: explicit `:focus-visible` outline is present in the HTML shell
  and covered by `tests/unit/test_cabinet_web_shell.py`.
- Responsive: Chrome screenshots at 1440x900 and 390x844 were visually checked.
  Mobile fixes were applied for top action wrapping, transcript stacking,
  viewport-width text wrapping, and non-overlapping assistant/search placement.
- No-overflow: mobile screenshots were re-captured after fixing top action
  overflow and transcript/detail text clipping.
- Contrast spot checks from CSS tokens:
  - text on background: `16.16:1`;
  - muted text on background: `7.83:1`;
  - primary text on primary background: `4.73:1`;
  - accent on background: `5.03:1`;
  - ready chip text on background: `8.16:1`;
  - partial chip text on background: `11.07:1`;
  - failed chip text on background: `6.23:1`.

## API Timing And List-To-Detail Evidence

Local `TestClient` timing with the sanitized cabinet fixture:

```text
list_status=200 list_ms=8.86 rows=4
detail_status=200 detail_ms=7.69 ready_id_matches_seed=True
```

The list response selected the ready meeting by status and the detail route
loaded that same meeting ID successfully.

## Evidence Hygiene

Tracked validation and research text were scanned for private account strings,
email patterns, exact private local paths, fixture-only external IDs, storage
object names, SHA strings, and raw private meeting identifiers.

```sh
rg -n "/Users/yshishenya|shishenya|professionals4-0|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|fixture-mediascribe|private-run-id|foreign-private|storage_object|sha256" \
  specs/016-meeting-dashboard-review/research \
  specs/016-meeting-dashboard-review/validation \
  --glob '!**/*.png'
```

Result: no matches.

PNG strings from tracked public/reference and implementation screenshot folders
were scanned with the same exact private-content patterns.

```sh
find specs/016-meeting-dashboard-review/research/reference-captures \
  specs/016-meeting-dashboard-review/validation/screenshots \
  -type f -name '*.png' -print0 \
  | xargs -0 strings \
  | rg -n "/Users/yshishenya|shishenya|professionals4-0|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|fixture-mediascribe|private-run-id|foreign-private|storage_object|sha256"
```

Result: no matches.
