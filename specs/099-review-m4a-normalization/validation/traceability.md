# Feature 099 Traceability Ledger

**Rule**: A task becomes `[X]` only after its outcome and focused evidence are
current. Green infrastructure health alone is never playback or user-path proof.

## Requirement coverage

| Requirement set | Primary task/evidence owner |
|---|---|
| FR-001–FR-007, FR-038, FR-042 | T021–T037 / `us1-first-party.md` |
| FR-003, FR-008–FR-009, FR-038–FR-040 | T038–T046 / `us2-manual-media.md` |
| FR-010–FR-013, FR-023–FR-024, FR-035, FR-040 | T047–T056 / `us3-automatic-recovery.md` |
| FR-026–FR-028, FR-033, SC-013–SC-014 | T057–T062 / `us7-ingest-boundary.md` |
| FR-014–FR-017, FR-033–FR-034, FR-041 | T063–T072 / `us4-backfill.md` |
| FR-011–FR-013, FR-021, FR-031, FR-037, FR-039–FR-040 | T073–T080 / `us5-failure-truth.md` |
| FR-018–FR-020, FR-030, FR-036–FR-037 | T081–T092 / `us6-lifecycle.md` |
| SC-001–SC-022 and cross-story gates | T093–T110 / cross-cutting validation receipts |
| FR-043, SC-023 | T117–T120 / `hotfix-worker-recovery.md`, `release-closeout.md` |
| Release and production truth | T111–T116 / `release-closeout.md` |

## Final requirement-quality reconciliation

| Checklist | Result | Final implementation evidence owner |
|---|---:|---|
| `checklists/requirements.md` | `16/16` | this FR/SC ledger and story receipts |
| `checklists/media.md` | `20/20` | `media-capability.md`, `media-matrix.md`, `local-e2e.md`, `performance.md` |
| `checklists/automation.md` | `22/22` | `us3-automatic-recovery.md`, `us4-backfill.md`, `browser-e2e.md` |
| `checklists/lifecycle.md` | `22/22` | `migration-evidence.md`, `us6-lifecycle.md`, `cleanup.md`, `performance.md` |
| `checklists/worker-restart-recovery.md` | `8/8` | T117–T120 recovery evidence |
| **Total** | **`88/88`** | requirement quality reconciled; runtime limitations remain explicit |

Checked items validate the requirement writing. Runtime acceptance comes only
from the code/test receipts below. T100 now has independent real Chrome and
embedded Play/Pause/seek, two-tab, reconnect, focus, responsive and
reduced-motion evidence in `browser-e2e.md`.

## Functional requirement implementation ledger

| ID | Final code/test anchor | Evidence state |
|---|---|---|
| FR-001 | canonical artifact model/publication in `normalization/service.py`; first-party workflow tests | green: `us1-first-party.md`, `local-e2e.md` |
| FR-002 | canonical-only cabinet selection in `cabinet/egress.py`; playback contract tests | green: `us1-first-party.md` |
| FR-003 | accepted manual media path plus single-source pipeline; supported format matrix | green: `us2-manual-media.md`, `media-matrix.md`, `local-e2e.md` |
| FR-004 | finalize scheduling, candidate validation and authoritative dual-source fallback | green: `us1-first-party.md`, `local-e2e.md` |
| FR-005 | independent playback/status projection and safe list/detail copy | green across code, real Chrome and embedded QA: `us3-automatic-recovery.md`, `browser-e2e.md` |
| FR-006 | probe, full decode, canonical profile and BMFF validator in `normalization/media.py` | green: `media-capability.md`, `media-matrix.md` |
| FR-007 | deterministic job identity, partial uniqueness and ready reuse | green: `us3-automatic-recovery.md`, `migration-evidence.md` |
| FR-008 | user title first and source-name fallback tests in manual upload | green: `us2-manual-media.md` |
| FR-009 | manual uploads remain excluded from calendar auto-match | green: `us2-manual-media.md` |
| FR-010 | duplicate finalize/pickup/refresh-safe durable identity | green: `us3-automatic-recovery.md` |
| FR-011 | retryable/terminal durable reason mapping and safe user copy | green: `us5-failure-truth.md` |
| FR-012 | objective unsupported/corrupt/no-audio classification | green: `media-matrix.md`, `us5-failure-truth.md` |
| FR-013 | local/attempt output remains hidden until validation and publication | green: `us1-first-party.md`, `us5-failure-truth.md` |
| FR-014 | automatic workspace inventory/reconciliation/backfill | green: `us4-backfill.md` |
| FR-015 | inventory planned actions/skips commit before dispatch | green: `us4-backfill.md` |
| FR-016 | backfill preserves existing meeting title/user edits | green: `us4-backfill.md` |
| FR-017 | missing/purged unsafe sources receive explicit skip truth | green: `us4-backfill.md` |
| FR-018 | canonical/candidate/attempt objects included in deletion and retention | green: `us6-lifecycle.md`, `cleanup.md` |
| FR-019 | requested/started/completed/failed/retried/skipped/backfilled audit receipts | green: `us6-lifecycle.md`, `us5-failure-truth.md` |
| FR-020 | audit/status/incident allowlists and no-secret-egress contract | green: `implementation-evidence.md`, `us5-failure-truth.md` |
| FR-021 | bounded media limits plus pre-download/free-capacity and pre-conversion reserve checks | green: `us5-failure-truth.md`, `performance.md` (`21 passed` capacity regression) |
| FR-022 | one durable list/detail projection across refresh/reconnect | green: code contract plus real two-tab Chrome and embedded app-close/relaunch observation in `browser-e2e.md` |
| FR-023 | four-attempt cycle plus automatic long-term retry/reconciliation | green: `us3-automatic-recovery.md` |
| FR-024 | retries reuse the existing meeting, revision, job and workflow identity | green: `us3-automatic-recovery.md` |
| FR-025 | supported/failure/idempotency/deletion validation suites | green: `media-matrix.md`, `cleanup.md` |
| FR-026 | normalization jobs arise only from accepted revision artifacts | green: `us7-ingest-boundary.md` |
| FR-027 | source fingerprint and media-revision lineage preserved through publication | green: `us7-ingest-boundary.md` |
| FR-028 | OpenAPI and finalize contracts contain no competing source-of-truth path | green: `us7-ingest-boundary.md` |
| FR-029 | disk-backed chunked source transfer, bounded subprocesses and streaming Range response | green: `us5-failure-truth.md`, `performance.md` |
| FR-030 | publication boundary hides temp, failed and unvalidated objects | green: `us6-lifecycle.md` |
| FR-031 | capacity/dependency/source/decode failures map to bounded durable reasons | green: `us5-failure-truth.md`, `performance.md` |
| FR-032 | transcript/summary and playback projections remain independent | code/embedded AX green: `us3-automatic-recovery.md`, `browser-e2e.md` |
| FR-033 | legacy regeneration uses retained accepted lineage only | green: `us4-backfill.md` |
| FR-034 | valid playback survives when source regeneration is unavailable | green: `us4-backfill.md` |
| FR-035 | row locks, deterministic lease and unique canonical convergence | green: `us3-automatic-recovery.md`, `migration-evidence.md` |
| FR-036 | meeting-lock serialization plus a no-TTL durable tombstone makes deletion/retention win queued/running/publishing/retry and response-loss late-object races | green: `cleanup.md`, `us6-lifecycle.md` |
| FR-037 | aggregate safe status/audit/incident metadata only | green: `us5-failure-truth.md` |
| FR-038 | canonical byte copy, layout-only remux and profile transcode decisions | green: `us2-manual-media.md`, `local-e2e.md` |
| FR-039 | unique usable/default audio selection; ambiguity fails without guessing | green: `media-matrix.md`, `us5-failure-truth.md` |
| FR-040 | every supported valid retained source converges automatically | green across synthetic and authorized inputs: `media-matrix.md`, `local-e2e.md` |
| FR-041 | legacy artifact validate/reuse/regenerate/unavailable plan | green: `us4-backfill.md` |
| FR-042 | accepted-source commit schedules normalization independently of processing | green: `us1-first-party.md`, `us7-ingest-boundary.md` |
| FR-043 | initial worker reconciliation admits only future-dated `worker_interrupted` retry-wait jobs through the existing retry/lease/dispatch path | focused green: `hotfix-worker-recovery.md`; production proof pending T120 |

## Success-criterion implementation ledger

| ID | Final code/test anchor | Evidence state |
|---|---|---|
| SC-001 | first-party candidate/fallback cannot publish ready before canonical validation | green: `us1-first-party.md`, `local-e2e.md` |
| SC-002 | manual supported matrix reaches canonical or explicit objective failure | green: `us2-manual-media.md`, `media-matrix.md` |
| SC-003 | playback route streams stored canonical only; no transcode/mix call | green: `us1-first-party.md` |
| SC-004 | duplicate finalize/retry/pickup keeps one logical record | green: `us3-automatic-recovery.md` |
| SC-005 | partial unique canonical index and loser cleanup | green: `migration-evidence.md`, `us3-automatic-recovery.md` |
| SC-006 | unsupported/no-audio/corrupt/over-limit cases reach bounded reasons | green: `media-matrix.md`, `us5-failure-truth.md` |
| SC-007 | every inventoried legacy row has action/skip before mutation | green: `us4-backfill.md` |
| SC-008 | deletion reports account for candidate/canonical/attempt states | green: `us6-lifecycle.md`, `cleanup.md` |
| SC-009 | manual-title precedence and fallback tests | green: `us2-manual-media.md` |
| SC-010 | no-secret-egress tests plus safe evidence review | green: `implementation-evidence.md`, `us5-failure-truth.md` |
| SC-011 | byte Range `206`, malformed-range rejection and no full-object read | green: endpoint/local E2E plus real Chrome/embedded Play and seek with `206` Range receipts in `local-e2e.md`, `browser-e2e.md` |
| SC-012 | transient failures retain source and retry without user action | green: `us3-automatic-recovery.md`, `performance.md` |
| SC-013 | accepted-source/revision identity enforced before job creation and pickup | green: `us7-ingest-boundary.md` |
| SC-014 | OpenAPI/finalize diff has no parallel upload/recording authority | green: `us7-ingest-boundary.md` |
| SC-015 | partial/temp/failed/unvalidated outputs never become playback egress | green: `us5-failure-truth.md`, `us6-lifecycle.md` |
| SC-016 | concurrent retry/backfill/workers converge via lease/lock/unique index | green: `us3-automatic-recovery.md`, `migration-evidence.md` |
| SC-017 | every tested deletion/retention overlap blocks late publication; response-loss and synthetic 365-day late arrivals are automatically removed | green: `cleanup.md` |
| SC-018 | source/capacity/decode cases have bounded status and cleanup | green: `us5-failure-truth.md`, `performance.md` |
| SC-019 | playback and transcript states project independently | green: code plus real Chrome/embedded status and player parity in `browser-e2e.md` |
| SC-020 | supported valid synthetic and authorized retained sources need no repair action | green: `media-matrix.md`, `local-e2e.md` |
| SC-021 | legacy inventory chooses reuse/regenerate/unavailable without fabrication | green: `us4-backfill.md` |
| SC-022 | normalization dispatch is committed independently from transcript processing | green: `us1-first-party.md`, `us7-ingest-boundary.md` |
| SC-023 | startup dispatches the eligible worker-interrupted job and preserves a different future-dated retry | focused green: `hotfix-worker-recovery.md`; production proof pending T120 |

The ledger has no undisclosed implementation gap. T100 recovered through the
documented manual top-level-navigation handoff and completed the real
Chrome/embedded local gate. Production proof remains T115. Feature 097 remains
deferred and was not used as evidence.

## GitHub issue sync

- Repository: `yshishenya/crisp`, matching `remote.origin.url`.
- Label: `feature:099`.
- Count: 120 open issues for 120 tasks.
- Identity: exact `T###` token. Issue numbers are not assumed contiguous by task
  because creation was parallelized.
- Validation: repository canon validator checked all current Spec Kit issues and
  returned `OK`.

### Полная сверка задач, issues и evidence (T109)

Authoritative read-back выполнен через GitHub REST API по label `feature:099`
с состоянием `all`, а не через отстающий search index. Результат:

- `116/116` task IDs имеют ровно по одному issue;
- отсутствующие task IDs: `0`;
- дубли task IDs: `0`;
- лишние issue task IDs: `0`;
- все `116` issues остаются открытыми до PR/merge evidence;
- canon post-hook: `OK (273 Spec Kit issue(s) checked)`.

| Task | Локальный статус | GitHub issue | Точный evidence receipt |
|---|---|---|---|
| T001 | готово | [#3349](https://github.com/yshishenya/crisp/issues/3349) — open | `validation/baseline.md` |
| T002 | готово | [#3348](https://github.com/yshishenya/crisp/issues/3348) — open | `validation/baseline.md` |
| T003 | готово | [#3350](https://github.com/yshishenya/crisp/issues/3350) — open | `validation/baseline.md` |
| T004 | готово | [#3353](https://github.com/yshishenya/crisp/issues/3353) — open | `validation/baseline.md` |
| T005 | готово | [#3351](https://github.com/yshishenya/crisp/issues/3351) — open | `validation/foundation-red.md` |
| T006 | готово | [#3352](https://github.com/yshishenya/crisp/issues/3352) — open | `validation/foundation-red.md` |
| T007 | готово | [#3354](https://github.com/yshishenya/crisp/issues/3354) — open | `validation/foundation-red.md` |
| T008 | готово | [#3355](https://github.com/yshishenya/crisp/issues/3355) — open | `validation/foundation-red.md` |
| T009 | готово | [#3356](https://github.com/yshishenya/crisp/issues/3356) — open | `validation/foundation-red.md` |
| T010 | готово | [#3360](https://github.com/yshishenya/crisp/issues/3360) — open | `validation/foundation-green.md` |
| T011 | готово | [#3358](https://github.com/yshishenya/crisp/issues/3358) — open | `validation/foundation-green.md` |
| T012 | готово | [#3357](https://github.com/yshishenya/crisp/issues/3357) — open | `validation/foundation-green.md` |
| T013 | готово | [#3359](https://github.com/yshishenya/crisp/issues/3359) — open | `validation/foundation-green.md` |
| T014 | готово | [#3361](https://github.com/yshishenya/crisp/issues/3361) — open | `validation/foundation-green.md` |
| T015 | готово | [#3362](https://github.com/yshishenya/crisp/issues/3362) — open | `validation/foundation-green.md` |
| T016 | готово | [#3363](https://github.com/yshishenya/crisp/issues/3363) — open | `validation/foundation-green.md` |
| T017 | готово | [#3364](https://github.com/yshishenya/crisp/issues/3364) — open | `validation/foundation-green.md` |
| T018 | готово | [#3365](https://github.com/yshishenya/crisp/issues/3365) — open | `validation/foundation-green.md` |
| T019 | готово | [#3366](https://github.com/yshishenya/crisp/issues/3366) — open | `validation/foundation-green.md` |
| T020 | готово | [#3367](https://github.com/yshishenya/crisp/issues/3367) — open | `validation/foundation-green.md` |
| T021 | готово | [#3368](https://github.com/yshishenya/crisp/issues/3368) — open | `validation/us1-first-party.md` |
| T022 | готово | [#3369](https://github.com/yshishenya/crisp/issues/3369) — open | `validation/us1-first-party.md` |
| T023 | готово | [#3370](https://github.com/yshishenya/crisp/issues/3370) — open | `validation/us1-first-party.md` |
| T024 | готово | [#3371](https://github.com/yshishenya/crisp/issues/3371) — open | `validation/us1-first-party.md` |
| T025 | готово | [#3372](https://github.com/yshishenya/crisp/issues/3372) — open | `validation/us1-first-party.md` |
| T026 | готово | [#3373](https://github.com/yshishenya/crisp/issues/3373) — open | `validation/us1-first-party.md` |
| T027 | готово | [#3374](https://github.com/yshishenya/crisp/issues/3374) — open | `validation/us1-first-party.md` |
| T028 | готово | [#3375](https://github.com/yshishenya/crisp/issues/3375) — open | `validation/us1-first-party.md` |
| T029 | готово | [#3376](https://github.com/yshishenya/crisp/issues/3376) — open | `validation/us1-first-party.md` |
| T030 | готово | [#3377](https://github.com/yshishenya/crisp/issues/3377) — open | `validation/us1-first-party.md` |
| T031 | готово | [#3378](https://github.com/yshishenya/crisp/issues/3378) — open | `validation/us1-first-party.md` |
| T032 | готово | [#3379](https://github.com/yshishenya/crisp/issues/3379) — open | `validation/us1-first-party.md` |
| T033 | готово | [#3381](https://github.com/yshishenya/crisp/issues/3381) — open | `validation/us1-first-party.md` |
| T034 | готово | [#3380](https://github.com/yshishenya/crisp/issues/3380) — open | `validation/us1-first-party.md` |
| T035 | готово | [#3382](https://github.com/yshishenya/crisp/issues/3382) — open | `validation/us1-first-party.md` |
| T036 | готово | [#3383](https://github.com/yshishenya/crisp/issues/3383) — open | `validation/us1-first-party.md` |
| T037 | готово | [#3384](https://github.com/yshishenya/crisp/issues/3384) — open | `validation/us1-first-party.md` |
| T038 | готово | [#3385](https://github.com/yshishenya/crisp/issues/3385) — open | `validation/us2-manual-media.md` |
| T039 | готово | [#3386](https://github.com/yshishenya/crisp/issues/3386) — open | `validation/us2-manual-media.md` |
| T040 | готово | [#3387](https://github.com/yshishenya/crisp/issues/3387) — open | `validation/us2-manual-media.md` |
| T041 | готово | [#3388](https://github.com/yshishenya/crisp/issues/3388) — open | `validation/us2-manual-media.md` |
| T042 | готово | [#3389](https://github.com/yshishenya/crisp/issues/3389) — open | `validation/us2-manual-media.md` |
| T043 | готово | [#3390](https://github.com/yshishenya/crisp/issues/3390) — open | `validation/us2-manual-media.md` |
| T044 | готово | [#3391](https://github.com/yshishenya/crisp/issues/3391) — open | `validation/us2-manual-media.md` |
| T045 | готово | [#3392](https://github.com/yshishenya/crisp/issues/3392) — open | `validation/us2-manual-media.md` |
| T046 | готово | [#3393](https://github.com/yshishenya/crisp/issues/3393) — open | `validation/us2-manual-media.md` |
| T047 | готово | [#3394](https://github.com/yshishenya/crisp/issues/3394) — open | `validation/us3-automatic-recovery.md` |
| T048 | готово | [#3395](https://github.com/yshishenya/crisp/issues/3395) — open | `validation/us3-automatic-recovery.md` |
| T049 | готово | [#3396](https://github.com/yshishenya/crisp/issues/3396) — open | `validation/us3-automatic-recovery.md` |
| T050 | готово | [#3397](https://github.com/yshishenya/crisp/issues/3397) — open | `validation/us3-automatic-recovery.md` |
| T051 | готово | [#3398](https://github.com/yshishenya/crisp/issues/3398) — open | `validation/us3-automatic-recovery.md` |
| T052 | готово | [#3399](https://github.com/yshishenya/crisp/issues/3399) — open | `validation/us3-automatic-recovery.md` |
| T053 | готово | [#3400](https://github.com/yshishenya/crisp/issues/3400) — open | `validation/us3-automatic-recovery.md` |
| T054 | готово | [#3401](https://github.com/yshishenya/crisp/issues/3401) — open | `validation/us3-automatic-recovery.md` |
| T055 | готово | [#3402](https://github.com/yshishenya/crisp/issues/3402) — open | `validation/us3-automatic-recovery.md` |
| T056 | готово | [#3403](https://github.com/yshishenya/crisp/issues/3403) — open | `validation/us3-automatic-recovery.md` |
| T057 | готово | [#3404](https://github.com/yshishenya/crisp/issues/3404) — open | `validation/us7-ingest-boundary.md` |
| T058 | готово | [#3405](https://github.com/yshishenya/crisp/issues/3405) — open | `validation/us7-ingest-boundary.md` |
| T059 | готово | [#3406](https://github.com/yshishenya/crisp/issues/3406) — open | `validation/us7-ingest-boundary.md` |
| T060 | готово | [#3407](https://github.com/yshishenya/crisp/issues/3407) — open | `validation/us7-ingest-boundary.md` |
| T061 | готово | [#3408](https://github.com/yshishenya/crisp/issues/3408) — open | `validation/us7-ingest-boundary.md` |
| T062 | готово | [#3409](https://github.com/yshishenya/crisp/issues/3409) — open | `validation/us7-ingest-boundary.md` |
| T063 | готово | [#3410](https://github.com/yshishenya/crisp/issues/3410) — open | `validation/us4-backfill.md` |
| T064 | готово | [#3411](https://github.com/yshishenya/crisp/issues/3411) — open | `validation/us4-backfill.md` |
| T065 | готово | [#3412](https://github.com/yshishenya/crisp/issues/3412) — open | `validation/us4-backfill.md` |
| T066 | готово | [#3413](https://github.com/yshishenya/crisp/issues/3413) — open | `validation/us4-backfill.md` |
| T067 | готово | [#3414](https://github.com/yshishenya/crisp/issues/3414) — open | `validation/us4-backfill.md` |
| T068 | готово | [#3415](https://github.com/yshishenya/crisp/issues/3415) — open | `validation/us4-backfill.md` |
| T069 | готово | [#3416](https://github.com/yshishenya/crisp/issues/3416) — open | `validation/us4-backfill.md` |
| T070 | готово | [#3417](https://github.com/yshishenya/crisp/issues/3417) — open | `validation/us4-backfill.md` |
| T071 | готово | [#3418](https://github.com/yshishenya/crisp/issues/3418) — open | `validation/us4-backfill.md` |
| T072 | готово | [#3419](https://github.com/yshishenya/crisp/issues/3419) — open | `validation/us4-backfill.md` |
| T073 | готово | [#3420](https://github.com/yshishenya/crisp/issues/3420) — open | `validation/us5-failure-truth.md` |
| T074 | готово | [#3421](https://github.com/yshishenya/crisp/issues/3421) — open | `validation/us5-failure-truth.md` |
| T075 | готово | [#3422](https://github.com/yshishenya/crisp/issues/3422) — open | `validation/us5-failure-truth.md` |
| T076 | готово | [#3423](https://github.com/yshishenya/crisp/issues/3423) — open | `validation/us5-failure-truth.md` |
| T077 | готово | [#3424](https://github.com/yshishenya/crisp/issues/3424) — open | `validation/us5-failure-truth.md` |
| T078 | готово | [#3425](https://github.com/yshishenya/crisp/issues/3425) — open | `validation/us5-failure-truth.md` |
| T079 | готово | [#3426](https://github.com/yshishenya/crisp/issues/3426) — open | `validation/us5-failure-truth.md` |
| T080 | готово | [#3427](https://github.com/yshishenya/crisp/issues/3427) — open | `validation/us5-failure-truth.md` |
| T081 | готово | [#3429](https://github.com/yshishenya/crisp/issues/3429) — open | `validation/us6-lifecycle.md` |
| T082 | готово | [#3428](https://github.com/yshishenya/crisp/issues/3428) — open | `validation/us6-lifecycle.md` |
| T083 | готово | [#3430](https://github.com/yshishenya/crisp/issues/3430) — open | `validation/us6-lifecycle.md` |
| T084 | готово | [#3431](https://github.com/yshishenya/crisp/issues/3431) — open | `validation/us6-lifecycle.md` |
| T085 | готово | [#3432](https://github.com/yshishenya/crisp/issues/3432) — open | `validation/us6-lifecycle.md` |
| T086 | готово | [#3433](https://github.com/yshishenya/crisp/issues/3433) — open | `validation/us6-lifecycle.md` |
| T087 | готово | [#3434](https://github.com/yshishenya/crisp/issues/3434) — open | `validation/us6-lifecycle.md` |
| T088 | готово | [#3435](https://github.com/yshishenya/crisp/issues/3435) — open | `validation/us6-lifecycle.md` |
| T089 | готово | [#3436](https://github.com/yshishenya/crisp/issues/3436) — open | `validation/us6-lifecycle.md` |
| T090 | готово | [#3437](https://github.com/yshishenya/crisp/issues/3437) — open | `validation/us6-lifecycle.md` |
| T091 | готово | [#3438](https://github.com/yshishenya/crisp/issues/3438) — open | `validation/us6-lifecycle.md` |
| T092 | готово | [#3440](https://github.com/yshishenya/crisp/issues/3440) — open | `validation/us6-lifecycle.md` |
| T093 | готово | [#3439](https://github.com/yshishenya/crisp/issues/3439) — open | `validation/media-capability.md` |
| T094 | готово | [#3441](https://github.com/yshishenya/crisp/issues/3441) — open | `validation/media-matrix.md` |
| T095 | готово | [#3442](https://github.com/yshishenya/crisp/issues/3442) — open | `validation/implementation-evidence.md` |
| T096 | готово | [#3443](https://github.com/yshishenya/crisp/issues/3443) — open | `validation/implementation-evidence.md` |
| T097 | готово | [#3444](https://github.com/yshishenya/crisp/issues/3444) — open | `validation/migration-evidence.md` |
| T098 | готово | [#3445](https://github.com/yshishenya/crisp/issues/3445) — open | `validation/macos-regression.md` |
| T099 | готово | [#3447](https://github.com/yshishenya/crisp/issues/3447) — open | `validation/local-e2e.md` |
| T100 | готово | [#3446](https://github.com/yshishenya/crisp/issues/3446) — open | `validation/browser-e2e.md` (Chrome + embedded Play/Pause/seek, two-tab, reconnect, focus, responsive, reduced-motion, Range) |
| T101 | готово | [#3448](https://github.com/yshishenya/crisp/issues/3448) — open | `validation/cleanup.md` |
| T102 | готово | [#3449](https://github.com/yshishenya/crisp/issues/3449) — open | `validation/performance.md` |
| T103 | готово | [#3450](https://github.com/yshishenya/crisp/issues/3450) — open | `validation/traceability.md` + `checklists/` |
| T104 | готово | [#3451](https://github.com/yshishenya/crisp/issues/3451) — open | `CHANGELOG.md` |
| T105 | готово | [#3452](https://github.com/yshishenya/crisp/issues/3452) — open | `docs/current-product-status.md` |
| T106 | готово | [#3453](https://github.com/yshishenya/crisp/issues/3453) — open | `validation/ponytail-review.md` |
| T107 | готово | [#3454](https://github.com/yshishenya/crisp/issues/3454) — open | `validation/implementation-evidence.md` |
| T108 | готово | [#3455](https://github.com/yshishenya/crisp/issues/3455) — open | `validation/implementation-evidence.md` |
| T109 | готово | [#3456](https://github.com/yshishenya/crisp/issues/3456) — open | `validation/traceability.md` (этот реестр) |
| T110 | готово | [#3457](https://github.com/yshishenya/crisp/issues/3457) — open до merge | `validation/pr-closeout.md` (явное разрешение, точный pre-stage path set, review/CI evidence) |
| T111 | ожидается | [#3458](https://github.com/yshishenya/crisp/issues/3458) — open | `validation/release-closeout.md` (ожидается) |
| T112 | ожидается | [#3459](https://github.com/yshishenya/crisp/issues/3459) — open | `validation/release-closeout.md` (ожидается) |
| T113 | ожидается | [#3460](https://github.com/yshishenya/crisp/issues/3460) — open | `validation/release-closeout.md` (ожидается) |
| T114 | ожидается | [#3461](https://github.com/yshishenya/crisp/issues/3461) — open | `validation/release-closeout.md` (ожидается) |
| T115 | ожидается | [#3462](https://github.com/yshishenya/crisp/issues/3462) — open | `validation/release-closeout.md` (ожидается) |
| T116 | ожидается | [#3463](https://github.com/yshishenya/crisp/issues/3463) — open | `validation/release-closeout.md` (ожидается) |
| T117 | готово | [#3616](https://github.com/yshishenya/crisp/issues/3616) — open | `validation/hotfix-worker-recovery.md` (focused startup regression) |
| T118 | готово | [#3617](https://github.com/yshishenya/crisp/issues/3617) — open | existing retry/lease/dispatch path in `normalization/` |
| T119 | готово | [#3618](https://github.com/yshishenya/crisp/issues/3618) — open | `validation/hotfix-worker-recovery.md` |
| T120 | ожидается | [#3619](https://github.com/yshishenya/crisp/issues/3619) — open | `validation/release-closeout.md` (canonical CI, release/deploy and production proof) |
| T121 | готово | [#3623](https://github.com/yshishenya/crisp/issues/3623) — open | `test_playback_normalization_restart.py`; `test_playback_normalization_postgres.py` |
| T122 | готово | [#3624](https://github.com/yshishenya/crisp/issues/3624) — open | `pickup.py`; migration `0026_skip_active_normalization_cleanup.py` |
| T123 | ожидается | [#3631](https://github.com/yshishenya/crisp/issues/3631) — open | `validation/release-closeout.md` |


## Evidence hygiene

Allowed: synthetic aliases, versions, profile/format facts, size/duration
buckets, states/reasons, counts, timestamps, command results and cleanup status.

Forbidden: raw audio, transcript/summary content, original filenames, object
keys/URLs, FFmpeg stderr or tag dumps, signed tokens, credentials, live secret
paths and private meeting data.

## Current task status

| Tasks | State | Receipt |
|---|---|---|
| T001–T004 | complete | `baseline.md`; Ruff/import/fixture assertions pass |
| T005–T020 | complete | `foundation-red.md`; `foundation-green.md` |
| T021–T037 | green | `us1-first-party.md` (`267 passed`; scoped US2 manual matrix follows) |
| T038–T046 | green | `us2-manual-media.md` (container `14/14`; integration `38 passed`; residue `0`) |
| T047–T056 | green | `us3-automatic-recovery.md` (`44 passed`; PostgreSQL `5 passed`; disposable DB residue `0`) |
| T057–T062 | green | `us7-ingest-boundary.md` (server `49 + 32`; macOS `121`; failures `0`) |
| T063–T072 | green | `us4-backfill.md` (`188 passed`; PostgreSQL/RLS `13 passed`; disposable DB residue `0`) |
| T073–T080 | green | `us5-failure-truth.md` (`191 passed`; container matrix `14`; integration `56 passed`; residue `0`) |
| T081–T092 | complete | `us6-lifecycle.md` (`144 passed`; real PostgreSQL force-RLS; residue `0`) |
| T093–T094 | complete | `media-capability.md`; `media-matrix.md` (14/14; `56 passed`; residue `0`) |
| T095–T096 | complete | `implementation-evidence.md` (`497 passed`; Ruff/compile/import pass; PostgreSQL residue `0`) |
| T097 | complete | `migration-evidence.md` (`42 passed`; direct RLS probe pass; residue `0`) |
| T098 | complete | `macos-regression.md` (Swift build pass; `139 passed`; no app reinstall) |
| T099 | complete | `local-e2e.md` (5 authorized working-copy scenarios; full decode; Range `206`; residue `0`; originals preserved) |
| T100 | complete | `browser-e2e.md`; `master-sync.md` (real Chrome and embedded preparing/available/unavailable, Play/Pause/seek, two-tab, reconnect, current-`.7` focus/responsive/reduced-motion, automatic temporary-failure recovery, terminal delete/no-resurrection and Range proof) |
| T101 | complete | `cleanup.md` (queued/running/publishing/retry plus response-loss and no-TTL late-object reconciliation; real Chrome delete while polling stayed terminal after delayed publication; residue `0`; originals preserved) |
| T102 | complete | `performance.md` (near-four-hour dual source; about 5 GiB package; `185.236s`; 1 CPU/1 GiB/6 GiB; OOM `0`; residue `0`) |
| T103 | complete | `80/80` original requirement-quality items plus the independent `8/8` startup-recovery hotfix checklist; runtime evidence remains separately scoped |
| T104–T105 | complete | `[Unreleased]` changelog plus implemented/not-released/backfill/app-impact/deferred-097/current-`.7` ownership truth |
| T106 | complete | `ponytail-review.md`; no new runtime dependency, shared-path reuse, bounded durable-tombstone debt recorded |
| T107 | complete | `implementation-evidence.md`; ordinary high-risk acceptance `110 passed`, PostgreSQL/RLS `19 passed`, feature 097 untouched |
| T108 | complete | `implementation-evidence.md`; `master-sync.md`; current-master canonical CI `ci_local_result=pass`, macOS `643/643`, server `1713 passed, 21 skipped`, PostgreSQL subset `23/23`, final normalization PostgreSQL file `12/12`, direct RLS probe pass, exit `0` |
| T109 | complete | `traceability.md`; GitHub REST `116/116`, missing `0`, duplicates `0`, canon validator `OK` |
| T110 | complete | `pr-closeout.md`; explicit user integration approval, exact pre-stage path-set digest, staged/unmerged preflight and three independent approvals |
| T111–T116 | pending | task-specific receipts listed in `tasks.md` |
| T117–T119 | complete | `hotfix-worker-recovery.md`; focused regression `7 passed`, related recovery suite `12 passed`, Ruff pass |
| T120 | pending | canonical CI, lean-diff review, release/deploy and production recovery receipt |
| T121–T122 | complete | active worker lease is excluded from SQLite/PostgreSQL cleanup selectors; focused SQLite suite `8 passed` |
| T123 | pending | canonical CI, release/deploy and production convergence receipt |
