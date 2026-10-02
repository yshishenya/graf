# Validation — F284

Source baseline: 77e6aed8ff79127d6e6b284ad18b58da5793ef51. Branch284-recording-continuity-playback. High-risk-product. Initial local validation was completed before the implementation commit; no external CI claim is made in that initial evidence. On 2026-10-02 the user explicitly authorized commit, push, PR and release. Subsequent exact-SHA evidence is recorded separately.

## Root localization and repair
- The600s timer formerly aged the last *transition*, while the log supervisor restarted every300s and could fail its3.5s two-hour snapshot. New default observer reads current CoreAudio input metadata every2s; no legacy log child is launched in native mode, including on unavailable metadata. App no longer resets accepted/manual-suppressed detector state on generation/failure. Full current snapshots mark absent sources inactive with15s grace and renew active evidence.600s remains for real observation loss. Child executable is attributed to containing outer app with exact bundleID registry filtering.
- Quota failures already had public storage_capacity_exceeded type but missing cabinet mapping/copy; fixed exact mapping and honest storage message plus existing /billing overview. No quota/payment/storage admission/state changes.
- Existing native player/queue already authorize retained audio. Detail now projects local open and binds native action to routeUUID/rowUUID; send/delete remain list-only. Existing lifecycle synchronization, hash/size/root checks and player revocation remain.

## Requirements gates
Independent reviewer: requirements3/3, safety8/8; analysisCRITICAL0/HIGH0/MEDIUM0; task ownership T001–T006 synced to issues7454–7459, umbrella7447. Issue canon validation passed300issues. Optional commit/context hooks skipped. Initial task list was reviewer draft; finalized after PASS. Supported prerequisite command used (installed script lacks --require-spec).

## Red evidence
- Quota regression failed before fix: expected storage_capacity_exceeded, actual unsupported_media.
- Detail browser regression failed before fix: authorized local copy expected1button, actual0.
- New Swift native/snapshot/timer/route tests required absent APIs and did not compile on old code; this is compile-time red evidence, not a claimed old runtime reproduction. Original runtime cause separately confirmed by prior system/app logs and historical slow-query reproduction. New executable emulation checks behavior after implementation.

## Passing checks
- Swift focused detector/composition/bridge/queue/deletion:213tests,0failures; native observer restart extra1test,0failures. After final composition cleanup,21focused composition/bridge/restart checks passed,0failures. Synthetic45min clock yields one offer, no timer expiry, preserves accepted/manual-suppressed state; full empty snapshot clears all old source state and emits end at15s; stale predicate false599/true600. Unavailable/native-empty stream never launches configured old-log-active children. Repeated observer generation does not replay accepted offer. Existing file missing, invalid M4A/track/path/readability, ownership/deletion tests pass. SHA256 comparison in the unchanged native-open authorization path was confirmed by source inspection; no separate wrong-SHA256 runtime test is claimed.
- Server isolated Postgres focused run:22passed in59.99s. Includes all public terminal reasons, durable list/detail parity, unvalidated candidate denial, deletion precedence, stored playback contracts, bounded transfer/digest unit checks and new quota render/copy checks.
  Exact focused selection: `UV_PROJECT_ENVIRONMENT=<existing local test environment> GRAF_TEST_WORKERS=2 bash apps/server/scripts/run_local_postgres_tests.sh --focused -q tests/contract/test_playback_status_contract.py tests/contract/test_cabinet_playback_contract.py tests/unit/test_playback_normalization_storage.py`. This22test run is16contract+6normalization storage tests, not billing_domain.
- Separate billing overview non-owner test:1passed (existing owner restrictions preserved); separate `tests/unit/test_billing_domain.py::test_storage_uses_exact_object_stat_and_rejects_overrun`:1passed, accepts exact boundary and rejects overrun; not attributed to22test run. Disposable container removed by runner; production data untouched.
- Browser local-recording-detail, local-recording-handoff, playback-refresh: PASS. Exact matching meeting, no browser/local action before native rows, lost access/removal/account change, server access_denied with stale native row, navigation/fragment refresh, retained keyboard focus, existing playback/comments and title edits covered.
- Ruff touched Python files, Spec Kit governance/bootstrap integrity, changelog fragments, git diff --check: PASS.

## Existing unrelated browser failure
local-recording-focus.test.cjs reaches timezone expectation and fails expecting05:30, actual03:30. Reproduced identically with original HEAD cabinet.js and user-time.js under the same browser runtime. Keyboard/local focus checks before that assertion pass; failure predates this change. No unrelated timezone fix folded in.

## Evidence boundaries
CoreAudio read-only probe: process list status0,40objects; no input active at probe time. The actual new `activeBundleIDs()` helper also returned available=true, active_count=0 in a read-only metadata probe. This proves API availability, not live Telemost capture. No new microphone capture performed; no private audio/transcript/paths/credentials stored here.
Dev harness status: active source7c4f844a983f2fe10a5f51fa695310acd47abac1, app GRAF Dev. It was not replaced: local-development requires an authorized implementation commit and clean exact SHA. Required PR governance-fast/macos-pr/pr-metadata, release-full, real controlled long-call acceptance, installed candidate and production deployment are still pending. Existing old call files remain intact; missing uncaptured seconds cannot be recovered. Quota still limits server audio, and local fallback requires retained authorized audio on this Mac plus updated desktop/cabinet.

## Convergence assessment
FR001–008 and SC001–004 compared against current code/tests/design after implementation. No missing code change found. No new implementation tasks required. Baseline timezone failure is outside these two bugs. Hardware/clean candidate/CI/release evidence remains explicitly pending, so feature is not declared shipped and tracker issues stay open.

Final independent review: PASS local code/regressions, requirements3/0+safety8/0. The access_denied stale-row gap was fixed and retested. Reviewer explicitly limits45min emulation to detector/start offers/timer decisions; no45min audio track was recorded. Full code/hardware/CI/release gates remain distinct.

## PR preflight correction
Implementation PR #7462 was opened on 2026-10-02. Initial governance-fast run37057788338 stopped in Development process preflight because spec.md lacked the required Legacy Impact section. The section now records removal of production log authority and retention of existing parser regression coverage. The local context category was also normalized to the supported high-risk-product value and its ownership/source pointer refreshed. No product behavior changed in this correction. Subsequent required checks must pass on the new head.
