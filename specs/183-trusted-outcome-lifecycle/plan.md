# Implementation Plan: Доверенные версии итогов по типам

**Branch**: `codex/183-trusted-outcome-lifecycle` | **Date**: 2026-08-23 | **Spec**: [spec.md](spec.md)

## Summary

Feature 183 меняет прежде всего фундамент пользовательской модели. Вместо одной
глобальной «принятой версии» встреча получает отдельный current pointer для
каждого устойчивого `template_key`. Внутренний candidate остаётся непубличной
транзакционной стадией: после полной автоматической проверки он атомарно заменяет
только свой type slot. Ошибка, stale source, удаление, timeout или конкурентный
запрос оставляют прежнюю ревизию видимой. Slice также делает только необходимые
compatibility UI/API изменения: убирает обычный accept/reject, показывает честные
slot states и переводит текущие browser/embedded readers на новый источник
правды. Полная Krisp-faithful композиция и toolbar принадлежат Feature 196.

Минимальная новая сущность — `meeting_summary_slots`; содержимое не копируется и остаётся в существующих `MeetingOutcomeSet`/`MeetingOutcomeItem`. Existing attempts, dispatch, Generation Call, source/deletion fences и tests переиспользуются. Обязательный user accept/reject удаляется из целевой продуктовой модели.

## Technical Context

**Language/Version**: Python 3.12; SQLAlchemy async; PostgreSQL; server-rendered Jinja/HTMX/JavaScript; Swift 6 embedded cabinet shell

**Primary Dependencies**: FastAPI, SQLAlchemy, Alembic-style repository migrations, PostgreSQL row locks/RLS, existing Temporal and Langfuse/LiteLLM outcome stack

**Storage**: Existing `meeting_outcome_sets`, `meeting_outcome_items`,
`meeting_outcome_generation_attempts`, `generation_calls`,
`dispatch_intents`; one new pointer/index table `meeting_summary_slots` and the
composite keys required to bind it. Feature 183 adds no canonical artifact,
receipt, GenerationCall-ownership or provenance-fingerprint schema. Feature 195
later adds owner-row receipts and complete attempt/outcome provenance without a
receipt table, fail receipt or duplicate summary payload.

**Testing**: pytest unit/contract/integration with disposable PostgreSQL; migration/backfill tests; current share/export/browser/embedded contract lanes

**Risk / Validation Lane**: high-risk product area — AI publication truth, Postgres/RLS, deletion, egress, concurrency and user-facing workflow

**Release Gate**: planning only in this turn. Implementation, commit, GitHub
issues, PR, prompt promotion, release and deploy require separate approval.
Feature 183 slot/migration/read/default-egress/CAS foundation is tested without
any successful model-generated receipt fixture. Its sole `ai_service.py`
publication entry point remains fail-closed and disconnected from the V1
generation path. Feature 195 owns the first positive receipt-backed publication,
P1–P4/full-schema vectors and canonical/call/calibration race proof after Feature
194 defines the canonical artifact. Internal/shadow
read/switch/refresh/evidence work is blocked on Features 182, 194, 195, 196, 197,
198, 200 and 202–203. Full public Krisp-parity Summary Workspace rollout through
Feature 204 additionally requires Feature 201 optional version-bound feedback and
Feature 205 editable completion/assignee/due controls; neither is a dependency of
initial prompt calibration or Feature 197 dispatch. Full parity with every
repeat-observed meeting-detail control additionally requires Features 209–211
for editable note blocks/comments, the grounded assistant and transcript
correction revisions; none is implemented by Feature 183.

**Target Platform**: GRAF server/web cabinet and the same route embedded in the macOS app

**Project Type**: server-owned web application embedded in a native macOS shell

**Performance Goals**: saved type switch requires no inference and uses one indexed pointer lookup; publication adds bounded row-lock work; no empty interval during replacement

**Constraints**: strict automatic verification before publish; no direct provider call; no user-facing candidate management; no runtime legacy guessing; deletion and egress remain truthful; metadata-only ordinary logs/evidence

**Scale/Scope**: existing user archive; multiple built-in/personal types per meeting; concurrency within a type and across types; one-time deterministic backfill

## Constitution Check

### Before Phase 0

- **Capture/consent**: not affected.
- **External AI boundary**: no new egress or provider; existing LiteLLM/Langfuse/Temporal boundaries are reused.
- **Deletion**: new slot pointers are lifecycle artifacts and must be purged/accounted with the meeting.
- **RLS/security**: every slot is workspace-scoped; pointer targets must belong to the same workspace, meeting and type.
- **Spec-driven delivery**: full specify → clarify → plan → checklist → tasks → analyze sequence is used.
- **Reference fidelity**: Feature 183 implements only bounded compatibility UI
  changes needed to remove accept/reject and expose truthful slot states. Feature
  196 owns literal reproduction of the approved Krisp UX/UI/IA composition,
  controls and state matrix. Independently written code, accessibility and
  third-party asset provenance remain gates.
- **Ponytail**: one pointer table is justified because a single meeting pointer cannot represent current revision per type. No second outcome ledger or content table is introduced.

### Installed-reference evidence boundary

The 2026-08-23 black-box pass used installed Krisp `3.15.6` (`ai.krisp.krispMac`, executable SHA-256 `eb5227e047bd78d9a3416a9d71c5def728f17f2fcfe8fb8c40c351423e441147`) across multiple ready, short, failed-transcript, generation-failure, template, action-item, list/search and paywall states. The metadata-only report stays outside git with private screenshots. Feature 196 may use the observed behavior, visible copy and screen geometry as implementation references. It may not reuse extracted assets, source, binaries, private APIs/protocols, secrets, private meeting content or proprietary model behavior.

**Gate result**: PASS for planning. Constitution 5.0.0 authorizes literal
observable UX/UI/IA parity; implementation remains in Feature 196 and still
requires accessibility and asset-rights review.

## Design Decisions

### 1. One current pointer per meeting and stable type

`MeetingSummarySlot(workspace_id, meeting_id, template_key)` owns `current_outcome_set_id`. One slot may additionally carry the meeting-default marker plus resolver source/version/time; this is the Feature 197→183 handoff and avoids re-resolving a viewer-dependent default during reads or egress. `template_key` is already stable across personal-template versions; each outcome keeps the exact template/version snapshot used. Composite/partial constraints bind the pointer and enforce at most one default slot; service checks remain defense in depth.

### 2. Candidate is internal, publication is automatic

Existing `revision_state=candidate` and attempt lifecycle remain internal. Feature
183 removes ordinary user accept/reject from the target contract, stops automatic
model writes and creates one fail-closed publication entry point plus a private
slot CAS primitive in `ai_service.py`. Existing `accepted` naming may remain only
for legacy compatibility; no new `accepted_by_user_id` or user-accept audit event
is fabricated. Feature 195 completes the same entry point after deterministic and
semantic gates; it does not add a second publisher or CAS implementation.

### 3. Compare-and-swap is slot-scoped

The expected pointer is `expected_current_outcome_set_id` for the target slot, not the meeting-global pointer. Different types can publish independently; two generations of the same type serialize on the slot row.

### 4. Last-known-good stays visible

Generation status belongs to the attempt. The slot pointer does not move until a new revision is fully valid and publishable. Failure never requires restoring the old result because it was never removed.

### 5. History is implicit in immutable outcome revisions

`supersedes_outcome_set_id` links successful revisions of the same type. No history payload/table, user history UI or rollback command is added in this program. Any later recovery feature must reuse the same fenced publication service.

### 6. Compatibility egress pins default type and exact revision

Feature 183 switches existing share/export readers to the persisted meeting-default slot. Feature 197 chooses and marks this slot before dispatch using explicit-meeting → authorized owner/personal → workspace precedence. A legacy meeting with no marker may run the existing versioned workspace resolver exactly once and persist the marker inside the egress transaction; it never consults the current viewer's selected/personal presentation preference. Resolution, validation and the exact type/outcome write happen at the grant/artifact transaction linearization point; existing artifacts do not silently follow future regeneration. Selecting arbitrary types and the complete egress UX belong to Feature 203.

### 7. Legacy fallback is retired

Backfill creates slots only from an explicit current pointer or another uniquely provable case. Ambiguous rows produce metadata-only reconciliation findings; ordinary reads never select «latest active» as a substitute.

### 8. Lifecycle state is orthogonal

The API separates result presence, generation attempt, source readiness/freshness and catalog availability. This keeps transcript failure distinct from summary failure, meeting source empty distinct from type-level no-supported-content, and a saved retired-format result readable without enabling ensure/refresh/default selection. Feature 196 owns presentation and presentation-intent fencing; Feature 183 owns the truthful server state.

### 9. Receipt finalization is a downstream extension of one entry point

Feature 183 owns only slot/source/deletion/expected-current preconditions, a
transaction-ready private CAS primitive and one fail-closed publication entry
point in `ai_service.py`; it cannot successfully publish a model-generated row.
Feature 195 extends that exact entry point with the downstream Receipt V1 model:
canonical pass JSON/schema/digest/finalized time only on the canonical artifact,
publication JSON/schema/digest/finalized time only on the type attempt, and only
publication schema/digest repeated on the outcome. It owns the first positive
finalization transaction, P1–P4/full-schema conformance vectors, deterministic
GenerationCall ordering and calibration/deletion race fixtures. There is no
receipt table, fail receipt, reservation row, second publisher or second CAS
implementation.

## Project Structure

### Documentation

```text
specs/183-trusted-outcome-lifecycle/
├── spec.md
├── plan.md
├── research.md
├── program-roadmap.md
├── program-backlog.md
├── krisp-parity-matrix.md
├── quality-and-evaluation.md
├── user-journey.md
├── prompt-pipeline.md
├── summary-profile-catalog.md
├── temporal-langfuse.md
├── completion-audit.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── lifecycle.md
│   ├── api.md
│   └── receipts.md
├── checklists/
└── tasks.md
```

### Expected implementation surface

```text
apps/server/src/twobrain_rec_server/
├── db/models/outcomes.py
├── db/models/meeting.py
├── outcomes/ai_service.py
├── outcomes/service.py
├── cabinet/{rendering.py,queries.py,egress.py,exports.py}
├── cabinet/web_routes/browser.py
├── cabinet/static/cabinet/cabinet.js
├── cabinet/templates/cabinet/pages/meeting_detail_content.html
├── api/{cabinet.py,schemas.py}
├── deletion/service.py
└── db/migrations/versions/0076_meeting_summary_slots.py

apps/server/tests/
├── contract/
├── integration/
└── unit/
```

**Structure Decision**: extend the existing outcomes module. Do not create a new service, framework, state store, prompt registry or content representation.

## Migration Strategy

1. Add slots and same-meeting/type integrity constraints without changing readers.
2. Backfill from explicit `Meeting.current_outcome_set_id`; use its exact key or metadata-normalize only a pointed keyless outcome to reserved `legacy-default` without changing content/source/provenance, and mark that exact compatibility slot as `legacy_pointer` meeting-default.
3. Produce metadata-only counts for missing target, missing type, cross-scope target and ambiguous legacy states.
4. Land slot-first dual-read: prefer slot; allow the explicit old pointer solely for a uniquely proven compatibility case. Newest-row inference is never allowed.
5. Run the deterministic post-backfill verifier and require a successful metadata-only ambiguity receipt.
6. Only then enable strict slot-only readers/share/export and remove the explicit legacy-pointer compatibility path.
7. Stop mutating the meeting-global pointer. Leave physical removal to a later compatibility migration after release evidence.

Reader code may land in slot-first dual-read form before backfill verification, but strict cutover cannot be implemented until T035's deterministic backfill verifier and ambiguity report complete successfully. T018 and T032 retain the one explicit-pointer compatibility path; T036 owns its removal from every reader/share/export owner after that implementation-sequencing gate. This requires no second runtime flag or state store: deployment runs the fail-closed migration/verifier before the strict-cutover application starts. `Meeting.current_outcome_set_id` is read-only compatibility state after cutover and is never updated by automatic publication.

Code rollback before cutover may keep the new table unused. Database downgrade is allowed only while every meeting has at most the single compatibility/default slot that can be represented by the preserved old pointer. If any meeting has additional type slots or a pointer that cannot be represented exactly, downgrade MUST fail closed and retain the table until a forward fix or explicit metadata-preserving export is approved. It must never reconstruct from newest outcome rows.

## Validation Plan

1. Domain model and migration fixtures for one type, multiple types, custom-template versions and legacy ambiguity.
2. Fail-closed/CAS matrix: every model-generated input is denied without slot or
   DispatchIntent mutation; DB-only non-model expected-current CAS covers success,
   stale, deleted, expired, duplicate, same-type race and cross-type independence.
3. Content integrity: internal candidates remain unreadable; old current content
   stays byte-identical; other type slots never change. Feature 195 separately
   proves receipt/provenance/slot/dispatch atomic completion.
4. Egress compatibility matrix: persisted meeting-default marker, one-time legacy workspace resolution, viewer-personal exclusion, exact transactional type/revision pin, refresh race, post-share regeneration, retired/stale/default-missing and pointer-null denial.
5. RLS/cross-workspace/cross-meeting/cross-type pointer substitution.
6. Deletion race at reservation, response persistence and publication.
7. Existing browser/embedded current-summary paths read the documented default slot and the same orthogonal state contract until Feature 196 adds the selector/presentation logic.
8. Focused PostgreSQL suite, then `infra/scripts/ci-local.sh --fast` at closeout.

## Program Dependencies

Feature 183 is independently testable as a slot/read/default-egress/CAS and
fail-closed boundary slice, but not independently releasable to users. The
normative implementation dependency DAG is [program-roadmap.md](program-roadmap.md);
the list below is a rollout sequence, not a linear hard-dependency chain:

```text
182 → 183
182 → 194
183 + 194 → 195
194 → 198
183 + 194 + 195 + 198 → 196 and 197
194 + 195 + 198 → 200
195 → 202
183 + 196 → 203
183 + 194 + 195 + 196 → 201
194 → 205 → Feature 196 editable action controls
194 + 195 + 198 + 199 + 202 → 208
197 + 200 + 201 + 202 + 203 + 205 → 204

Feature 201/205 do not block initial Feature 200 prompt calibration or internal
shadow runs; they do block full public Krisp-parity Workspace GA.
```

### Contract ownership

| Feature | Owns | Hands off |
|---|---|---|
| 183 | per-type slot, named composite scope keys, private slot-CAS primitive, one fail-closed `ai_service.py` publication entry point, immutable revision lineage and default-type compatibility resolver | exact slot/read/CAS boundary; no positive model-generated publication |
| 194 | canonical evidence-backed artifact, `MeetingCanonicalSourcePointer`, source-authority/ontology schemas and deterministic validators | validated artifact/schema/source-pointer bundle and cutover from newest-result queries |
| 195 | durable PINNED LiteLLM/Temporal/Langfuse invocation, calibration-registry schema/storage/exact lookup/finalizers, request/verifier identity, retry/ambiguity semantics, real artifact/attempt/call/candidate production and the first positive receipt-backed completion of the existing `ai_service.py` entry point | one fully reconstructed publication transaction that locks source before slot and invokes Feature 183's CAS primitive; no second publisher |
| 196 | meeting-detail/list/type/evidence core IA, capability hosts, continuity states and accessibility | user intent to ensure/refresh/read plus host state for later Share/action integrations |
| 197 | transcript-ready trigger, default resolution, exact-source BCP-47 transcript-regeneration command, mutation of Feature 194's source pointer and bounded automatic recovery | idempotent summary ensure and transcript-job intents plus saved-active-type-only fan-out |
| 198–199 | built-in/personal type catalog and versioned profile snapshots | stable type key plus exact template version |
| 200 | human-grounded dataset/evaluator/manifests, qualification and promotion eligibility, production calibration/root activation/revocation and serialized protected-label promotion gate | exact promoted root + activation + pass-event binding or rollback target |
| 201 | optional version-bound result/claim feedback | non-blocking production quality signal; required before full public Workspace GA, not initial prompt calibration |
| 203 | actual Share header action/dialog/lifecycle plus arbitrary selected-type export contracts | explicit type/revision egress request and final integration into the Feature 196 host |
| 204 | staged production rollout/SLO/rollback | full public Workspace only after 201/205 gates |
| 205 | canonical mutable action lifecycle | one authorized/idempotent/expected-version command path; required before editable tasks and full public Workspace GA |
| 206 | cross-meeting Action Hub | projection over Feature 205; not a core-rollout blocker |
| 207 | cross-meeting continuity summary | optional proof-bound two-meeting delta; not a core-rollout blocker |
| 208 | generated subject-scoped request/slot/receipt/RLS lifecycle | optional private outcome isolated from shared slots; not a core-rollout blocker |
| 209 | editable note-document block/comment revision lifecycle | functional Krisp block menu without mutating generated result truth; full-surface parity after core rollout |
| 210 | grounded meeting assistant query/session/call/receipt lifecycle | functional contextual assistant with evidence and no hidden inference/state mutation |
| 211 | transcript correction and canonical-source revision lifecycle | functional transcript-row edit controls plus safe stale/regeneration fan-out |

## Post-Design Constitution Check

- One justified pointer table; content and lifecycle ledgers are reused.
- Automatic publication increases risk but is fenced by stricter deterministic/evidence/source/deletion/concurrency checks and keeps last-known-good visible.
- No prompt/model or external dependency policy is changed.
- Slot deletion and legacy reconciliation are explicit.
- This slice changes only the compatibility browser/embedded surfaces needed for
  slot truth and accept/reject removal. Authorized literal observable KRISP
  reproduction, including the split Notes/type control and full toolbar/state
  matrix, remains Feature 196 scope.

**Gate result**: PASS for tasks generation. Implementation remains blocked until checklists and analyze are clean.

## Complexity Tracking

| Complexity | Why needed | Rejected simpler alternative |
|---|---|---|
| One new `meeting_summary_slots` table | A meeting can have one current revision per type; the existing single pointer cannot represent that invariant | Querying latest outcome per type is race-prone, makes publication implicit and resurrects legacy rows |
| Slot-scoped CAS | Prevents stale same-type replacement while allowing parallel different types | Meeting-global lock would serialize unrelated types and still not store separate current pointers |
