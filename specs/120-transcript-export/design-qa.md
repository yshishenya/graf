# Feature 120 Design and Runtime QA

**Date**: 2026-07-21
**Risk lane**: significant/high-risk product and content-egress change
**Data boundary**: synthetic meeting metadata and synthetic Russian text only;
no transcript content, provider identifiers, credentials, or private screenshots.

## Browser QA

The cabinet meeting-detail shell was rendered through the production template,
CSS, and JavaScript and served with a synthetic content-export response. The
flow was exercised in headed Chromium with the repository Playwright wrapper.

| Check | Evidence | Result |
|---|---|---|
| Single entry point | One enabled `Экспорт` action opens one modal dialog | PASS |
| Initial focus | Focus lands on the `Экспорт` heading, so the dialog starts at its title on narrow screens | PASS |
| Focus return | `Escape` closes the dialog and returns focus to the triggering export button | PASS |
| Scope-first IA | Transcript, summary, and combined choices expose readiness before format | PASS |
| Format compatibility and grouping | Four labelled groups separate readable TXT/MD, tables CSV/XLSX, structured JSON, and subtitles SRT; incompatible summary/combined formats are absent | PASS |
| Summary evidence option | Disabled for transcript and enabled for summary | PASS |
| Option semantics | CSV/XLSX/JSON structural fields cannot be disabled; SRT timestamps are mandatory; transcript requests force `include_evidence=false` | PASS |
| Metadata-only preview | Dynamically shows scope, readiness, format purpose, speaker/timestamp/evidence behavior, separate transcript/summary revision prefixes, language, `01:01:01` duration, and response-only storage; no meeting content | PASS |
| Copy text | Uses the same audited export endpoint with a TXT request, writes the response to the clipboard, and announces `Текст скопирован.` in the live status region | PASS |
| Failure state | Synthetic `export_revision_stale` keeps the dialog open, restores submit focus, and shows safe Russian recovery copy | PASS |
| Successful response | Synthetic TXT response starts one attachment download with the server filename | PASS |
| Duplicate submission | Submit is disabled and the dialog is marked busy while the request is active | PASS |
| Narrow viewport | Chromium at 390 by 844 CSS pixels reports document width 390 and viewport width 390 | PASS |
| 200% zoom | At the 390-pixel viewport, simulated 200% page zoom keeps document width at 390 with the dialog scrolling internally rather than causing horizontal page overflow | PASS |
| Console | Zero warnings/errors on the normal page and dialog path; the intentional HTTP 409 failure produces only the expected browser network error | PASS |
| Motion and contrast | Existing reduced-motion and forced-colors/high-contrast rules cover the export controls | PASS |

A synthetic mobile screenshot was visually inspected and then removed with the
transient Playwright session artifacts; it contained no private meeting data
and is not required for source control.

This engineering pass covers SC-012: keyboard/focus behavior, accessible names,
live status, narrow layout, 200% zoom, reduced-motion/high-contrast rules, and
screen-reader-oriented structure. It does not satisfy the representative-user
success outcome in SC-014. That external study remains explicitly open as T059
and is required before general release.

## Long-meeting serializer measurement

A synthetic 7,200-turn, 7,920-second transcript was rendered in-process for all
six transcript formats. Measurements use `time.perf_counter` and Python
`tracemalloc`; they are local engineering evidence, not production SLOs.

| Format | Render time | Peak traced memory | Bytes |
|---|---:|---:|---:|
| TXT | 80.0 ms | 4.7 MiB | 1,006,841 |
| MD | 110.3 ms | 5.5 MiB | 1,057,252 |
| CSV | 175.7 ms | 13.5 MiB | 2,256,307 |
| XLSX | 5,986.6 ms | 1.6 MiB | 572,683 |
| JSON | 372.3 ms | 31.2 MiB | 5,905,805 |
| SRT | 93.9 ms | 5.6 MiB | 1,166,582 |

The XLSX serializer is deliberately write-only and has the lowest measured
peak memory, trading CPU time for bounded memory. JSON is the largest
provider-neutral fidelity snapshot and remains below one second for this
synthetic input. Rendering runs outside the async event loop, and no generated
artifact is persisted by GRAF after the response.

The shared overlap detector also processed a synthetic worst-shape timeline of
7,200 mutually overlapping valid rows in 69.2 ms locally, producing 7,200
non-merged overlap turns without the former pairwise scan.

## Final validation

The post-review diff passed `infra/scripts/ci-local.sh`: 594 macOS tests, 2,013
parallel server tests with one skip, and 35 strict PostgreSQL/RLS tests with one
skip, followed by Ruff, Python compile, Compose validation, and the deployment
evidence scan. The final marker was `ci_local_result=pass`.

The representative-user study required by SC-014 remains a separate
pre-release gate; green engineering CI does not satisfy it.

## Embedded macOS download regression

The production regression was reproduced in the installed GRAF client: the
web export flow created a `blob:` attachment, but the embedded route policy
classified the WebKit download navigation as an unsupported cabinet route and
replaced the meeting detail with `Раздел недоступен`.

The corrected native flow was validated at three levels on 2026-07-22:

| Check | Evidence | Result |
|---|---|---|
| Route boundary | Focused tests accept only an explicit main-frame `blob:` download from an allowed meeting-detail source; iframe, non-download, non-blob, external, login, and API targets remain denied | PASS |
| Destination safety | Focused tests strip path components, avoid overwrites, and choose a unique flat filename in the destination directory | PASS |
| WebKit handoff | A standalone WebKit smoke created a real `Blob`, clicked an attachment link, transitioned through `WKDownload`, and verified the saved bytes | PASS |
| Signed GRAF runtime | A locally signed `2026.07.22.1` build exported the production owner meeting to one 14,654-byte TXT file in Downloads while the meeting detail and playback timeline stayed visible | PASS |
| Metadata-only diagnostics | Native log recorded `cabinet_download_started` and `cabinet_download_finished` without filename, path, transcript content, or meeting identifier | PASS |

No production meeting content, filename, identifier, or screenshot is stored in
the repository evidence. This engineering hotfix does not replace the T059
representative-reviewer study required before general release.
