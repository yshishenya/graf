# Quickstart: Feature 183 validation

This is the future implementation validation guide. It does not authorize provider calls, prompt promotion, commit or deploy.

## Preconditions

- Work from `codex/183-trusted-outcome-lifecycle`.
- Feature 182 evidence contract is available at the planned base SHA.
- Disposable PostgreSQL test environment only.
- No private transcript/output is printed or committed.

## Exact focused commands after implementation

Run contract/unit checks that do not require PostgreSQL:

```sh
cd apps/server
uv run --extra dev --extra evaluation pytest -q \
  tests/contract/test_summary_type_slot_contract.py \
  tests/contract/test_summary_type_slot_migration_contract.py \
  tests/contract/test_summary_template_ui_contract.py \
  tests/unit/test_summary_templates.py \
  tests/unit/test_summary_candidate_revisions.py
cd ../..
```

Run the database-backed matrix only through the disposable PostgreSQL helper:

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused -q \
  tests/integration/test_meeting_summary_slots.py \
  tests/integration/test_meeting_outcomes_generation.py \
  tests/integration/test_cabinet_meeting_outcomes.py \
  tests/integration/test_outcome_generation_workflow.py \
  tests/integration/test_transcript_export_egress.py \
  tests/integration/test_recording_share_public_link.py \
  tests/integration/test_meeting_outcomes_migrations.py \
  tests/integration/test_meeting_outcomes_deletion.py \
  tests/integration/test_rls_postgres_migrations.py
```

Run the embedded macOS contract target selected by the repository package:

```sh
swift test --package-path apps/macos \
  --filter DesktopMeetingShellWebViewBoundaryTests
```

T043 records aggregate-only source-scan results from these exact commands:

```sh
rg -n 'current_outcome_set_id\s*=' apps/server \
  --glob '!**/.venv/**' --glob '!**/__pycache__/**'
rg -n 'accepted_by_user_id\s*=' apps/server \
  --glob '!**/.venv/**' --glob '!**/__pycache__/**'
rg -n 'current_outcome_set_id' apps/server \
  --glob '!**/.venv/**' --glob '!**/__pycache__/**'
rg -n -i 'latest.*(outcome|summary)|(outcome|summary).*latest|newest.*(outcome|summary)|most_recent.*(outcome|summary)|summary-candidates/.*/accept' \
  apps/server --glob '!**/.venv/**' --glob '!**/__pycache__/**'
rg -n 'MeetingOutcomeSet|meeting_outcome_sets' apps/server \
  --glob '!**/.venv/**' --glob '!**/__pycache__/**'
rg -n -U --pcre2 '(?s)(MeetingOutcomeSet|meeting_outcome_sets).{0,800}(created_at|generated_at).{0,160}(\.desc\(\)|\bDESC\b|\.first\(\)|\.limit\(1\))|(created_at|generated_at).{0,160}(\.desc\(\)|\bDESC\b).{0,800}(MeetingOutcomeSet|meeting_outcome_sets)' \
  apps/server --glob '!**/.venv/**' --glob '!**/__pycache__/**'
rg -n -U -i --pcre2 '(?s)order\s+by.{0,240}(created_at|generated_at)\s+desc' \
  apps/server --glob '!**/.venv/**' --glob '!**/__pycache__/**'
rg -n -i 'transcript|raw_response|prompt_definition' \
  specs/183-trusted-outcome-lifecycle/validation
rg -n -i '/Users/|Yandex\.Disk|Evidence/Meetings|feature-183-repeat-audit|\.png\)' \
  specs/183-trusted-outcome-lifecycle
git diff -- specs/183-trusted-outcome-lifecycle
git diff --check
```

The pointer and query scans are review inputs rather than automatic zero-match
assertions. The broad `MeetingOutcomeSet|meeting_outcome_sets` inventory is
authoritative: for every matching file, T043 inspects every enclosing query,
raw SQL statement, imported alias and helper, then follows every local helper
caller. The narrower regexes are regression aids and cannot substitute for that
inventory; this explicitly covers current `MeetingOutcomeSet.created_at.desc()`
and `generated_at.desc()` shapes, `.first()`/`.limit(1)`, Python sorting,
aggregate-max selection and renamed helpers. Every match across source,
scripts, tests and migrations is classified by path and symbol in
`validation/privacy.md`. The closed allowlist is limited to the
legacy field declaration, historical migrations, deletion compatibility and
explicitly named migration/legacy contract fixtures. Operational scripts have
no allowance: T036 must migrate or retire
`apps/server/scripts/reconcile_initial_outcomes.py` and replace the candidate
accept flow in `apps/server/scripts/prove_meeting_outcome_live.py` with the
slot-backed ensure/read proof (or retire that script if a successor fully owns
the proof). Aliases, raw SQL, exports, outcomes, API/cabinet/browser code and
embedded helpers are all in scope. A contract test must fail when a new
unclassified model/table query owner or newest-row helper appears. Strict
cutover requires zero unallowlisted
runtime or operational-script reads/writes, zero user-accept publication and
zero newest-row fallback.

## 1. Static contracts

Run focused contract tests covering migration shape, slot uniqueness, orthogonal
API state semantics, no user accept UI dependency, no duplicate post-transcript
trigger, exact egress pinning and forbidden fallback. This Feature 183 suite does
not claim selector, transcript-language or Share-host UI completion; their
browser/embedded executable matrix is Feature 196 acceptance.

Expected: all pass; source scan finds no new direct provider endpoint or second outcome content model.

The feature-spec privacy pass is both mechanical and manual. The path scan must
find no local screenshot/evidence path. A reviewer must inspect the complete
feature diff for user-provided record titles, participant names, transcript or
summary excerpts and replace any such value with an opaque evidence ID before
recording aggregate-only evidence. The diff itself is never copied into the
validation receipt.

## 2. Migration and backfill

Fixtures:

1. explicit current pointer with valid type;
2. explicit current pointer without a type, normalized to reserved `legacy-default`;
3. multiple saved types after migration;
4. missing target;
5. cross-workspace/meeting/type target;
6. multiple plausible legacy rows;
7. deleted/deleting meeting;
8. migration rerun.
9. exactly one legacy pointer is marked meeting-default with `legacy_pointer` provenance; two default markers are rejected.
10. an empty/null-current slot whose workspace differs from its meeting is rejected by the composite meeting FK.
11. `legacy_incomplete` is readable only through the exact
    `migrated_legacy_read_only` slot plus recomputed migration proof; an
    unpointed/ambiguous legacy row is not returned by ordinary reads, and the
    migrated row cannot create new egress.

Expected: only uniquely proven rows create slots; content hashes/text remain unchanged; ambiguity is metadata-only; rerun is idempotent.

## 3. Publication matrix

Feature 183 has no successful model-generated publication fixture. Exercise its
private slot primitive only with DB-only non-model revisions:

- exact expected-current/scope/source/access/deletion match moves target slot
  `R1 → R2` once and records same-type supersession without finalizing a model
  receipt or `DispatchIntent`;
- expected-current mismatch, source/media/speaker/deletion change and target
  substitution leave the slot unchanged with a typed conflict;
- repeated equivalent DB-only CAS is idempotent; two same-type writers have one
  winner, while different-type fixtures may move independently;
- every model-generated candidate returns `verified_runtime_unavailable`, leaves
  all slots and `DispatchIntent` unchanged and never exposes candidate content;
- missing/invalid schema, evidence, entailment of any canonical claim, critical
  omission, prompt/template state, dependency or provider outcome remains
  fail-closed with the old current result;
- same-key replay creates no extra attempt, dispatch, publication or inference;
  the same key with different durable identity returns a stable conflict;
- schema inventory proves Feature 183 added no canonical artifact, receipt,
  GenerationCall-membership, calibration, fingerprint, receipt-table or receipt-
  reservation path;
- no receipt-vector artifact exists in Feature 183, so no draft checksum can be
  mistaken for positive publication evidence. Feature 195 creates the first
  schema-valid P1–P4/full-matrix conformance corpus from scratch.

Expected: no empty interval, no mutation of a non-target type and zero successful
model-generated publication in Feature 183. Feature 195 owns the first positive
receipt-backed publication, P1–P4/full-schema vectors, pending-publication
finalization and canonical/call/calibration/deletion race matrix.

The downstream first-positive handoff is incomplete until its promoted
conformance corpus also proves all of these exact paths:

- text-topic projection batch zero transforms the durable `FocusRequestV1` into
  one frozen final `FocusV1`; later batches cannot resolve again, sample topics
  or fall back to `all_material`;
- zero eligible, zero selected and topic no-match/ambiguity persist strict
  `AttemptTerminalEvidenceV1`, make zero presentation/candidate/receipt writes
  and preserve the same-type last-known-good slot;
- `CriticalityPolicyV1` covers source/candidate/canonical/profile-expansion
  populations; decision/action state, proposal/idea/option disposition,
  requires-approval, effective date and `UncertaintyV1` survive through visible
  receipt only when supported;
- `SourceContextPolicyV1`, `MeetingIntentV1`, mixed-audience intersection, every
  privacy data-class/materiality/mode action, exact evidence-display mapping and
  `DetailBudgetV1` reject every authority/leakage/critical-drop challenge; a
  blocked critical privacy item fails the type rather than disappearing; a
  free-form `my_name_and_role` or `only_me` value cannot set authenticated
  subject, speaker mapping, owner or authorization; the profile×applicable
  master-clause manifest has no missing cell;
- every `ProfileContractV1` row and legal/illegal secondary pair reconstructs
  the exact composite hash, every section semantic rule, section merge, risk
  maximum, prohibition/criticality union and unchanged primary budget; the full
  body/hash and clause closure are byte-identical in projection, synthesis,
  verification, rendered content and receipt. A secondary-profile mutation must
  change all three logical requests, and a per-profile prompt label must fail;
- every call binds an evaluated/promoted `GatewayRouteBindingV1` and exact
  `RequestSettingsV1`/actual provider/model plus the pinned endpoint/serializer/
  translator/default-drop request-compiler identity, while a replacement
  immutable verifier carries the complete `VerifierIdentityV1` body/hash and
  complete pre/post `LangfuseEvaluatorReadbackV1` bodies/hashes (including
  Langfuse evaluator ID/numeric version); every external prompt/route/schema/
  validator object is an exact `ImmutableArtifactBindingV1`. A replacement
  verifier or
  calibration identity creates a new
  manifest/extraction identity and passes old/new finalizer/race fixtures;
  OpenAI `max_retries=0`, LiteLLM `num_retries=0` and zero automatic
  gateway/provider/transport retries are read back, with Temporal as the only
  bounded inference retry authority;
- Temporal evidence proves explicit PINNED Worker Deployment config,
  ramp/current/rollback, complete replay corpus, repeated Visibility plus
  DrainageStatus/no-poller/not-current/not-ramping/zero-open removal gates and
  Versioning-Override-vs-Reset-with-Move recovery. Priority/Fairness is recorded
  as Public Preview; self-hosted evidence reads back
  `matching.useNewMatcher=true`, `matching.enableFairness=true` and
  `matching.enableMigration=true`, proves backlog migration and exercises the
  separate-queue/custom-scheduler fallback when capability is unavailable.
  Flags alone do not pass readiness. Run five equal-weight trials independently
  for Workflow and Activity queues with one dominant plus 20 small ready keys,
  at least 500 post-warm-up starts per key, every share ratio and simultaneous
  Bonferroni-corrected 95% Wilson bound inside `0.80..1.20`, per-key p99 at most
  `2 × unloaded-small-key p99 + 30s`, and automatic/background starts at least
  their 10% floors. Run at least three weighted `0.5/1/2/4` trials with at least
  10,000 starts and 500 per key; every observed/expected ratio and simultaneous
  bound must be inside `0.85..1.15`. Restart workers, exclude the 120-second
  convergence window and repeat every share/statistical/latency/lane-floor gate;
  a missing floor or inconclusive row fails readiness and keeps the fallback.
  Langfuse evidence proves
  pending-owner-claim→sending→confirmed|ambiguous CAS, crash-window reconciliation,
  W3C same-trace parent binding and five distinct day-7/day-8 judge drift runs
  without repeated inference. Every weekly judge drift run first freezes one
  complete `VerifierDriftPlanV1` with dataset/split, expected head, thresholds
  and five run/item/invocation plans; unplanned or cherry-picked runs cannot
  move freshness. Feature 200 separately proves five fresh full
  task-pipeline runs with new GenerationCalls; that qualification dataset uses
  at least 60 suitable/30 unsuitable items per profile, while 20/10 remains
  shadow-only. Judge stability is a different family: five independent judge
  runs intentionally evaluate the same complete frozen task-output manifest.
  Judge repeats cannot substitute for five fresh task runs, and a single item
  or partial output cannot substitute for the complete frozen judge manifest.
- promotion evidence reconstructs a candidate-root-bound
  `RootQualificationRecordV1` and exact protected-label read-back
  `RootPromotionEventV1`, then emits and replays its complete
  `ImmutableArtifactBindingV1`; omitting either body/binding, replacing the
  binding with a bare hash or embedding root-naming measured evidence inside
  the candidate activation manifest fails the non-cyclic gate;
- every newly generated revision requires one same-scope attempt, complete
  normalized provenance tuple, root/activation/resolved-run manifests and
  publication receipt; this positive provenance schema/finalizer check belongs
  to Feature 195 and is absent from Feature 183.
- the exact successful promotion-event binding byte-equals the canonical
  parent, every GenerationCall, resolved-run manifest, terminal evidence,
  renderer input and both receipts; unknown ID, schema/event-version mismatch,
  body/hash mutation, wrong qualification/activation, failed read-back or
  hash-only substitution fails before egress/finalization and preserves the old
  slot;
- every production/candidate/judge model phase proves network-free prepare,
  one-attempt invoke and the durable `prepared → sending → response_recorded |
  failed_pre_egress | ambiguous` machine. Crash/timeout after sending performs
  no resend; only authenticated no-upstream-egress proof permits a bounded new
  successor call with an exact predecessor link;
- pre-promotion baseline/candidate runs carry the complete sealed
  `CandidateEvaluationAuthorityV1` and can write evaluation evidence only;
  production calls carry `PromotedRootBindingV1`. Swapping either authority or
  mutating a slot/receipt/DispatchIntent from evaluation fails before egress;
- a lock-wait-across-deadline DB fixture proves each receipt and weekly-PASS
  writer obtains a fresh `clock_timestamp()` in its last conditional write;
  transaction/statement/caller time cannot authorize stale publication, and
  returned issued time/body/digest byte-equal stored values;

## 4. Read and egress

- Explicit ready type reads return exact slot current revision.
- Missing type returns honest state, not newest outcome.
- No explicit type resolves documented default.
- Existing share/export pins exact default type/outcome revision; arbitrary selected-type egress is deferred to Feature 203.
- A source-revision fixture with three active saved types, one retired saved type
  and one unsaved catalog type marks all three active old-source slots stale,
  keeps their old revisions readable and blocks new share/export without
  mutating another slot. The retired result becomes stale/read-only and neither
  it nor the unsaved type is generated. Feature 197 acceptance later proves one
  coalesced replacement intent per active saved available type, default/current
  first; Feature 195 proves each verified replacement publishes only to its own
  slot.
- Feature 194 acceptance backfills one unambiguous
  `MeetingCanonicalSourcePointer`, removes runtime newest-result selection and
  locks it before summary slots. Feature 197 acceptance proves authenticated/
  CSRF BCP-47 regeneration, same-key join/different-identity conflict, business-
  hash/job/Workflow identity separation, successor retry ordinal/predecessor and
  `REJECT_DUPLICATE`; reload recovers through monotonic authorization-first GET/
  event polling without work. Provider submission persists correlation before a
  `maximum_attempts=1` Activity, definitive rejection is terminal, possible
  acceptance stays wait-only until required lookup/signed callback reconciliation,
  and only confirmed success moves one source pointer with no retired/unsaved fan-out.
- Result presence, generation attempt, source state and catalog availability remain independent: retired saved result is `ready + retired`; transcript failure is not a summary failure; source-empty is not type-level no-supported-content; blocked/deferred/ambiguous never expose unsafe retry.
- A retired custom type keeps its exact saved revision readable but denies ensure/refresh/default resolution and compatibility egress.
- Default resolution consumes the persisted meeting-default slot. Only legacy meetings without a marker may resolve and persist the versioned workspace default once; it never changes with the viewer's selected/personal presentation preference.
- Regeneration after share/export does not alter prior artifact/link.
- In a controlled share/export-versus-refresh race, the artifact/grant transaction pins exactly the revision current at its linearization point; the losing side never mutates that pair afterward.
- Saved result remains readable with LiteLLM/Langfuse/Temporal unavailable.
- An exact `migrated_legacy_read_only` current remains readable without AI
  dependencies, but cannot create new share/export; a verified refresh replaces
  the slot with a new `complete` revision and clears the legacy proof without
  rewriting the old row.
- Shared generation/ensure rejects `my_actions`, `private_self` and every
  subject-dependent control. Feature 183 exposes no positive `my_actions`
  endpoint/control and therefore creates no attempt/dispatch/model call for it;
  authenticated filtering is acceptance scope for Feature 205/196 after
  canonical actions and trusted subject mapping exist.

Migration downgrade must fail closed when multiple slots cannot be represented by the preserved legacy pointer.

## 5. Security/deletion

- Cross-workspace/meeting/type pointer substitution denied without existence leak.
- Shared recipient cannot generate/refresh unless policy explicitly permits.
- Feature 183 has no `my_actions` read route to probe. Feature 205/196 later owns
  authorization-before-filtering and the same no-existence-leak denial shape for
  inaccessible meeting, missing mapping and another subject's action.
- Deletion during reservation, response persistence and publication cannot create a current slot.
- Entering `deleting` immediately blocks summary read and new egress before physical purge; retained GenerationCall/Langfuse/Temporal copies remain truthfully distinguished.
- Transcript-regeneration jobs, replacement ProcessingResult/transcript artifacts
  and provider evidence pass same-workspace composite ownership/RLS and GRAF
  tombstone/purge accounting; retained Temporal observability is reported as a
  separate dependency state, not a readable meeting artifact.
- Provider errors exposed outside approved retained boundaries are bounded metadata codes.
- RLS tests use real PostgreSQL roles/context.

## 6. Existing regression suites

Run the repository PostgreSQL helper for:

- summary candidate revisions;
- meeting outcomes generation;
- outcome dispatch/workflow;
- cabinet meeting outcomes;
- transcript/share/export egress;
- deletion integration.

Then run the feature-focused contract/unit suites and `infra/scripts/ci-local.sh --fast` before closeout.

## 7. Evidence receipt

Record only:

- branch and exact SHA;
- migration revision ID;
- command/test names and counts;
- invariant/backfill aggregate counts;
- no-private-content scan result;
- known limitations and blocked downstream features.

## Pass criteria

- All SC-001–SC-012 in [spec.md](spec.md) are mapped to passing checks.
- Feature 183 analyze gate is `CRITICAL 0 · HIGH 0 · MEDIUM 0`.
- No commit, issue sync, PR or rollout until explicit approval.
