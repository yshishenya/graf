# Feature 168 Spec Kit analysis gate

**Mode:** implementation follow-up consistency review; no issue sync, commit,
PR or production change.

## Constitution alignment

Pass: the spec preserves server-owned credentials, read-only access, tenant/RLS
isolation, fail-closed provider state, deletion truth, metadata-only evidence,
manual Record/Stop and no auto-join/auto-record/calendar writes. Google launch
is explicitly blocked on owner/OAuth/policy dependencies.

## Requirement-to-task coverage

| Requirement range | Covered by | Status |
|---|---|---|
| FR-001..FR-006 | T004–T013, T020–T024 | covered |
| FR-007..FR-012 | T014–T019, T030–T036 | covered/gated |
| FR-013..FR-017 | T010–T013, T025–T026 | covered |
| FR-018..FR-021 | T020–T024 | covered |
| FR-022..FR-025 | T027–T029 | covered |
| FR-026..FR-033 | T030–T036 | covered/gated |
| FR-034..FR-038 | T041–T045 | covered; visual/runtime closeout recorded |
| FR-039..FR-043 | T046–T058 | covered; provider truth, home upcoming, IA, action-state and post-runtime remediation recorded |
| FR-044..FR-045 | T059–T064 | covered; approved policy implemented and every uncertified family fails closed as `Скоро`; each future provider promotion remains independently gated |
| NFR-001..NFR-007 | T006–T007, T015, T018, T022, T026, T037–T040, T064 | covered; NFR-006 has a repeatable p95 regression |
| AC-001..AC-013 | T013, T019, T024, T029, T036–T039, T041–T053, T064 | covered/gated |

## Findings

| ID | Category | Severity | Location | Finding | Resolution |
|---|---|---|---|---|---|
| A168-01 | dependency | CRITICAL before Google launch | `spec.md` FR-033 / plan | Google requested data-sharing disclosures. The corrected privacy policy is live, but the homepage FAQ is not yet published, the review-thread reply is pending and the exposed client secret still requires rotation. | Keep T067, T068 and T072 open; do not equate External/In production or a live privacy page with Google approval. |
| A168-02 | validation | HIGH | `research.md` / quickstart | Local Google authorize/catalog/select/full+incremental sync/upcoming/disconnect/reconnect evidence exists, and deterministic 410/429/revoked mappings are covered synthetically, but dedicated-account recovery and production-wide access remain unproven. | Keep metadata-only local receipt; require T036 and production rollout/rollback evidence before launch. |
| A168-03 | scope | HIGH | US2/US6 | Local Google full and incremental runtime coverage is observed, while revoked-access recovery remains synthetic-only. | Keep the provider gated; do not call it production-ready until the remaining external receipts exist. |
| A168-04 | implementation delta | HIGH | approved disconnect/sync/provider decisions | The owner approved local-only disconnect, a 7-day/365-day horizon, maximum 20 selected calendars and real-E2E-only production connect actions. | T059–T064 are implemented and validated. T062 proves current fail-closed catalog truth; promoting any provider remains conditional on that provider's own real matrix. |
| A168-05 | implementation risk | MEDIUM | maintenance worker | A new operation table is unnecessary. | Ponytail rule applied: reuse source state, existing audit, maintenance worker and one RLS operation. |
| A168-06 | runtime UX | HIGH | provider preset/view model | A configured Google client must not retain the dependency blocker, while an absent client must remain fail-closed. | Safe runtime-availability boolean now flows from app settings to the existing provider payload; both branches are tested and observed. |
| A168-07 | reconnect lifecycle | HIGH | `calendar/service.py` / T036 | Reconnecting one provider account must not create duplicate active sources or lose selected calendars. | Active source matching the hashed account subject is reused; sealed envelope and catalog are refreshed while selected IDs are preserved. Synthetic Postgres coverage added. |
| A168-08 | desktop UX | MEDIUM | `CalendarTray.swift` / US7 | Krisp has an upcoming/menu-bar context layer, while GRAF had no native tray surface. | Added one native status item/popover over the existing desktop endpoint; no new auth, cache, provider adapter or recording control. Visual popover and AX labels were inspected in the local dev app. |
| A168-09 | provider truth | HIGH | `calendar/capabilities.py`, `service.py`, `worker.py` | EWS and Bitrix24 were labeled supported but had no validation/worker adapter; VK WorkSpace used CalDAV in UI but missed worker routing. | Central provider metadata now drives CalDAV adapter routing; VK is covered; every uncertified family is non-interactive `Скоро`; an explicit local Google override is certification-only. |
| A168-10 | main journey | HIGH | `/meetings`, `/desktop/meetings` | The authoritative upcoming event projection existed in API/settings/tray but was absent from the main user surface. | Reuse the settings preview projection on both meeting-list shells, with compact safe states and no second persistence path. |
| A168-11 | settings IA | MEDIUM | `calendar_settings.html` | Connection, provider catalog, reminders and preview formed one long engineering-oriented screen; unsupported providers opened actionless dialogs. | Reorder into source → behavior → add source → advanced details; group controls by user goal; keep unsupported services readable but non-interactive. |
| A168-12 | action state | HIGH | source card / provider dialog JS | Sync remained clickable while queued/syncing; native invalid forms lacked adjacent status; cancelled forms retained entered values in DOM. | Disable duplicate sync, add safe adjacent validation, clear cancelled forms and preserve focus return. |
| A168-13 | concurrency | HIGH | `calendar/sync.py` | Provider I/O under the source row lock could delay disconnect and let stale work approach persistence. | Mark syncing separately, perform I/O without the lock, then lock and re-check the source before persistence; race regression passes. |
| A168-14 | provider resilience | HIGH | provider pagination/retry | Unbounded or repeated page tokens could loop; transient reads lacked a bounded shared retry policy. | Cap pagination at 20 pages, fail closed on repeated tokens, and use three attempts with bounded jittered backoff for retryable reads. |
| A168-15 | embedded layout | MEDIUM | calendar settings CSS | A hidden legacy navigation node left the content in grid column two, producing a blank 208px column in the real WebView. | Collapse the existing grid to one column when the legacy node is present; computed embedded width and visual runtime now agree. |
| A168-16 | responsive UX | MEDIUM | cabinet rail JS | Resizing an already-loaded desktop page to 390px retained the expanded rail and left only 214px for content. | Reuse the existing surface breakpoint and collapse on its `change` event; 390px now has a 64px rail, 326px content and zero overflow. |
| A168-17 | main action | MEDIUM | home upcoming rendering | The safe meeting route existed, but the visual fixture showed only “Есть ссылка” and did not prove the primary action. | Render the existing internal endpoint as `Подключиться`; sealed synthetic evidence proves the CTA without retaining a raw URL. |
| A168-18 | incremental sync | HIGH | `calendar/normalize.py`, `calendar/worker.py` | Real incremental Google sync returned 17 descriptions longer than the 4000-character persistence contract. Flush failed with SQLSTATE 22001 and the precommitted worker state remained `syncing`. | Bound shared normalized description/location fields to the existing schema, finalize unexpected worker failures as stale/failed, log only the exception class and prove the same 550-change incremental run reaches `synced`. |
| A168-19 | performance coverage | HIGH | `spec.md` NFR-006 / `tasks.md` | The three settings/sync p95 thresholds had no direct task or receipt; only the inherited 098 context budgets were measured. | T064 adds one warmed disposable-PostgreSQL regression: 20 cached projections and 20 acknowledgements pass 500 ms/1 s/300 ms p95 gates without provider I/O. |
| A168-20 | artifact consistency | MEDIUM | `spec.md`, `plan.md`, `tasks.md`, provider matrix | `Пока недоступно` conflicted with the approved single label `Скоро`; T032 still named provider revoke; T063 appeared dependent on open T062; production and local-certification availability were conflated. | Align on `Скоро`, remove provider revoke from T032, scope T063 to implemented policy work and document the explicit local-only Google certification override. |

## Unmapped tasks

None. T036 and T067–T072 remain intentionally open external/release closeout
gates. Issue sync was not invoked; the current convergence slice was executed
locally without commit, PR or production mutation.

## Metrics

- Functional requirements: 45; FR-044..FR-045 are mapped to T059..T064.
- Non-functional requirements: 7; all mapped.
- Acceptance criteria: 13; all mapped.
- Implementation tasks: 72, ordered by story and path; 7 remain open.
- Critical pre-launch blockers: client-secret rotation, public FAQ publication,
  Google review-thread resubmission/approval, dedicated test-account recovery
  and production rollout/rollback evidence.

## Gate result

The artifacts and implementation are internally consistent for the tested,
feature-gated slice. They are not approval to issue-sync, commit, deploy, or
claim Google production readiness.
