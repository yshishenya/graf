# End-to-End User Journey

This is the target journey for the complete 183–211 program, not the
implementation scope of Feature 183 alone. Feature 183 owns per-type
current-revision truth; 194 owns canonical evidence-backed intelligence; 195
owns verified runtime; 196 owns list/search and meeting-detail interaction; 197
owns automatic first generation and transcript regeneration; 198 owns built-in
profiles; 199 owns personal formats; 200 owns evaluation/promotion; 201 owns
feedback; 202 owns privacy/security closeout; 203 owns arbitrary selected-type
share/export; 204 owns rollout; 205 owns canonical mutable action commands; 206
owns optional cross-meeting action follow-through; 207 owns optional continuity;
208 alone owns optional subject-scoped generated outcomes; 209 owns a
human-editable note-document overlay and comments; 210 owns the grounded
meeting assistant; and 211 owns non-destructive transcript correction
revisions. Features 209–211 are required for full observed-surface parity but
do not block the first trustworthy generated-summary rollout.

## 0. Find or resume a meeting

- `Встречи` keeps Upcoming above history and exposes readiness, duration, participants and date before opening.
- `Отложенные` (`Later` in English), filters and sorting narrow the list without changing meeting content. Supported facets are star, date, contains, company, type, tags and folders; facets combine with AND and values inside one facet with OR. Sort is date, duration or last modified with newest/oldest direction and stable meeting-ID tie-break.
- Global `⌘K` search starts with recent searches, then shows loading, exact results or a clear no-results state; inaccessible meetings never leak into the list. It searches only permitted indexed title/metadata/content. Duplicate titles remain distinct through stable meeting identity plus date and available participant/duration context; a stale result that loses access fails closed instead of opening another same-title meeting.
- Opening a meeting restores this user's last successful `Итоги`/`Расшифровка` view and last successful summary type for that meeting. A failed attempt never becomes the remembered type.
- Browser and embedded macOS routes share the same server-owned meeting identity and result; native Record/Stop controls remain outside this post-meeting state.

## 1. Meeting ends

The meeting remains usable immediately: recording/player and transcript processing status are primary. Feature 197 resolves explicit meeting → policy-authorized owner/personal → workspace precedence, atomically marks that slot as the persisted meeting default with resolver provenance, and does not show mock notes.

```text
Transcript not ready → «Обрабатываем встречу»
Transcript ready → dispatch default summary exactly once
```

No user decision is requested.

## 2. First default result

### Preparing

- Summary tab exists and explains that the first result is being prepared.
- Transcript and player remain available.
- Status does not steal focus or create a blocking modal.
- A sub-300 ms completion does not flash a spinner. After 300 ms a stable preparing state appears; after 5 seconds copy explains that processing continues in the background and the user can leave safely.
- Repeated clicks/events coalesce into the same durable intent. Leaving the page does not cancel a generation or cause a second call on return.
- Auto-summary/open-after-meeting/automatic-title policies are independent. Capture auto-start and excluded applications remain under the existing capture policy; changing any summary policy never silently changes recording behavior or sharing defaults.

### Ready

- Verified result appears automatically.
- Page does not jump; a bounded live announcement says that summaries are ready.
- Result follows the selected type's exact section contract. The generic
  outcome-first/decisions/actions/risks/questions hierarchy is a planning
  ontology, not a universal set of visible headings; Auto alone keeps the
  fixed `Action Items` then `Key Points` shell.
- Unsupported optional sections are hidden; the interface never leads with a
  schema dump or a table filled with `не указано`.
- Auto preserves the ordered labels `Action Items` then `Key Points`, but emits
  only non-empty sections: actions occur only in the first and every other
  selected outcome only in the second. If neither has supported content, the
  type ends as `no_supported_content` and no empty result is published.

### Top strip and exact-revision actions

- The primary strip matches Krisp: `Итоги`/`AI Notes` is a tab whose adjacent
  icon+chevron is a separate type-menu button; `Расшифровка`/`Transcript` is the
  peer tab. The tab and menu button are separate keyboard/focus targets.
- Copy serializes only the exact authorized revision currently displayed. If a
  refresh completes during the click/clipboard operation, the copied payload and
  announcement remain bound to the old painted `outcome_set_id`.
- For a ready selected type, Refresh is in the right action cluster immediately
  left of Copy. The slot stays present but busy/disabled during updating,
  blocked, deferred or ambiguous work. A missing type has no Refresh control;
  its typed wait, safe retry or transcript recovery appears in the status panel.
- The observed compact `RU` control remains in the top strip even while
  `Итоги` is selected and is always named `Язык расшифровки`. It opens the
  Krisp-faithful `Transcribe in correct language` popover, warns that
  regeneration may take up to 30 minutes and enables the explicit `Regenerate`
  action only after a valid language change. Selection alone starts no work.
- The enabled action submits only Feature 197's authenticated/idempotent command
  with CSRF protection, the exact expected canonical source revision, canonical
  BCP-47 selected language and bound access/deletion/policy epochs. A
  duplicate joins the same durable transcript job; stale-source conflict reloads
  current language/state, and an ambiguous submission remains wait-only until
  authoritative reconciliation. Feature 196 cannot create its own job path.
- `RU` belongs only to transcript reprocessing. It never calls summary
  `ensure`/`refresh` and never masquerades as summary output language. Notes
  output language remains an independent Feature 198 profile/generation policy;
  any later user control for it must be designed outside this observed top strip.
- Share is a meeting-header action owned by Feature 203. Opening it freezes the
  displayed type/revision/language; a background refresh may announce a newer
  version but never retargets the open dialog. Feature 196 owns only its exact
  placement and always-present disabled host for every accessible meeting until
  Feature 203 supplies the capability. Policy restrictions keep that host visible
  with a reason; only access loss, deletion or no-existence-leak states hide it.
  Feature 196 has no Share command, dialog or lifecycle of its own.
- A dismissible `Reformat AI notes to Meeting Minutes?` banner appears exactly
  when Auto is ready, Meeting Minutes is available and no result exists for the
  target template version. Rendering the banner is local and starts no model
  call. `Try it out` is the single ensure+selection intent; dismiss is remembered
  only for the exact user+meeting+target-template-version and status/error copy
  always takes precedence. If the target already has a stale result, the banner
  is not shown and no second ensure is created: the existing type stays readable,
  its source-recovery state is shown, and Refresh becomes available only after
  the source is current under the normal ready-type contract.
- Missing, stale, retired, access-lost, deleting, permission and dependency
  states use the exact enabled/disabled/read-only matrix in
  `krisp-parity-matrix.md`; unavailable actions explain why and never enter fake
  pending state.

### Failed, source-empty or selected type has no supported content

- Failure names the safe next action; raw provider details are hidden.
- `meeting_source_empty` is one meeting-level state when the transcript has no useful source at all.
- `no_supported_content` is scoped to one selected type and never hides ready results of other types.
- A selected `no_supported_content` type remains selected. Its own empty state is
  primary, or the Transcript/player is primary only when its typed recovery says
  so; another ready type is merely a switch target and is never substituted into
  the selected type's content surface.
- Retry is offered only when safe; ambiguous provider outcome is not blindly retried.
- A blocked, deferred, ambiguous or `no_supported_content` refresh never removes
  the old current revision. Copy remains available for that displayed revision;
  Share depends on the revision's own freshness/access/deletion policy, not on
  the failed background attempt. Refresh/language stays disabled or follows the
  typed `next_action` until that attempt is terminal/reconciled. Transcript
  language remains governed by source/transcription state, not by a summary
  attempt.
- Without an old revision, those same states disable Copy/Share and
  expose only their typed wait/safe-retry/switch/transcript recovery. They never
  substitute another type or latest candidate; the transcript-language control
  remains independently available only when transcription recovery permits it.
- Transcript failure is a separate upstream state: recording/player remain available when possible, Copy/summary actions are disabled, and only a valid transcript-language/retry recovery is offered. Transcript language/regeneration is never labelled or treated as summary output language; its reprocessing impact and expected duration are explicit.

### Source changed

- After successful transcript `Regenerate`, every active saved type whose result
  uses the old canonical source becomes `stale`; the previous revision remains
  readable with a clear `Для предыдущей версии расшифровки` state.
- Feature 197 creates exactly one coalesced replacement intent for each active
  saved available type, prioritizing the persisted default/current type. It never
  generates unsaved catalog types. Retired types remain stale/read-only and are
  not regenerated; Feature 195 publishes each verified replacement only to its
  own slot.
- New share/export is unavailable until the replacement is current; existing pinned artifacts do not mutate silently.

## 3. Read and verify

- Every displayed canonical claim and action has a source action when evidence
  exists; criticality never removes evidence affordance from a non-critical
  displayed claim.
- Source action seeks to the canonical segment/player timestamp.
- Transcript and player behavior executes `PX-01`–`PX-10` in
  `krisp-parity-matrix.md`: play/pause, seek/scrub, advertised speed, speaker
  lanes/filter, preparing/unavailable/error, keyboard/VoiceOver and focus
  restoration must match in browser and embedded macOS. Static reference images
  do not count as proof of those interactions.
- `Вернуться к итогам` restores type, position, focus, player position and play/pause state; no source jump starts playback implicitly.
- Evidence navigation pins `outcome_set_id`, outcome-item ID/kind and canonical segment ID. A refresh that completes while the transcript is open never navigates the user. Return fallback is deterministic: exact outcome item if still current/readable → new-current item with the same canonical segment ID and item kind → first item in the same semantic section → new-current summary heading. If no current result remains accessible, transcript stays primary. The final focus target is the restored item/control or chosen section/summary heading, and one polite announcement explains that the summaries were updated when fallback occurred.
- Unknown owner/date stays unknown; the UI does not prompt the user to resolve routine uncertainty.
- Proposal/idea/option disposition, `requires approval`, effective date and
  every material uncertainty remain visibly distinct; smooth prose cannot erase
  them. Gaps appear as calm `Нужно уточнить`, never an unsolicited modal.
- Meeting intent, audience, privacy, focus and detail policy are resolved from
  the selected type and defaults. Mixed audience shows only the intersection
  authorized for every requested audience. These controls may change emphasis,
  never canonical truth or rights. Receipt V1 accepts
  only `facts_only`; model-authored analysis is unavailable until its own
  versioned phase/verifier/manifest/content/receipt and policy contract exists.

## 4. Switch summary type

### Type already saved

- Selection is instant.
- No dispatch/model call.
- Selected state, title and content always refer to the same type.

### Type not yet saved

- Selector moves to that `template_key` and immediately shows its own honest empty/preparing state.
- That selection itself calls `POST ensure` once with a stable idempotency key;
  there is no second `Generate` confirmation. GET/read never starts inference.
- Other saved types remain one switch away.
- Exactly one equivalent generation is active.
- Reload/close does not cancel or duplicate it. On return, the last successful type is primary and the preparing type remains visible in status; if no successful type exists or the route explicitly requests that type, its preparing state remains primary.
- On success, result appears automatically and becomes the remembered successful type only if this request still owns the latest presentation-intent version. After a newer user selection or navigation, success updates availability silently and does not move visible/remembered context.
- On failure, no other type is mislabeled as this one. If this request still owns the latest presentation intent and a prior ready type exists, GRAF restores it automatically and reports that the selected format failed while current summaries were preserved. After newer intent, failure reports status without moving the user. Without a prior result, transcript/player remain primary.

## 5. Refresh current type

- `Обновить итоги` applies only to the current ready type and occupies the
  stable right-action position immediately left of Copy.
- Old same-type result remains fully readable with a small `Обновляем` status.
- A stale result remains readable but has no new-egress Refresh path until the
  canonical source is current; the source-recovery/fan-out status owns that
  transition. This prevents a stale manual refresh from racing the transcript
  replacement and makes the reformat banner's absent-versus-stale behavior
  deterministic.
- While updating or non-terminal blocked/deferred/ambiguous, that same control is
  visible but disabled/busy; it does not move or become a second request path.
- Missing types omit Refresh entirely; their status panel owns wait/safe-retry/
  transcript recovery after the selection-triggered ensure.
- Success atomically replaces content without focus/scroll jump.
- Failure keeps old content and says `Предыдущая версия сохранена`.
- Immutable previous revisions remain internal; the normal interface has no history/undo or accept/reject workflow.
- Duplicate refresh clicks are disabled/coalesced immediately. A user-visible Cancel is absent unless the runtime can prove real durable cancellation before ambiguous egress.

## 5a. Use action items

- Every task is a canonical action, not text parsed again from the rendered summary.
- Each displayed action row keeps task text, assignee, due-date control and its
  canonical evidence timestamp together. The timestamp opens Transcript at that
  source without starting playback.
- Completion, assignee and due date are edited inline and persist after reload and across the per-meeting/global action views.
- Unknown assignee/date remains unknown until a user explicitly edits it; the model does not invent a value.
- Editing a task does not rewrite the immutable summary revision or silently train/promote a prompt.

## 5b. Optional feedback

- The feedback surface is visible but never interrupts reading or asks the user
  to approve generated summaries. It first asks `How were the:` and offers only
  sections actually visible in the pinned revision. Choosing a section starts
  no write; it expands that exact section's five-point emoji radio group.
- Each emoji has a text label, and the group names the exact result revision and
  section key. Closing before a rating writes nothing.
- Choosing 1–3 offers optional categorical reasons; choosing any later value
  updates the same exact version-bound record rather than creating votes.
- Escape/close before the first choice writes nothing. After save, close keeps
  the value; `Удалить оценку` is the only clear action. Pending, failed,
  conflict and offline retry states keep the last saved value visible and focus
  on the same control.
- Feedback is bound to the exact meeting/type/revision/bundle and a closed
  result/section/claim scope. The Krisp-parity path uses the exact visible
  section key; an optional claim-scoped path cannot alias that record. Feedback
  never changes the result, starts inference or promotes a prompt.

## 6. Share or export

Owned by Feature 203; Feature 183 only makes existing compatibility egress resolve the documented default type and exact revision.

- Action clearly names the current type.
- GRAF pins exact current revision at action time.
- The pin occurs at the authoritative grant/artifact write: refresh committed before that transaction may be shared, while refresh committed after it cannot alter the created link/artifact.
- Later refresh does not silently change an existing link/artifact.
- If no explicit type context exists, GRAF shows the documented default before egress.
- Recipient/access level, scope and exact shared type are visible before creation; unavailable permissions are explained without exposing private existence. Capability levels distinguish edit, comment, full meeting view and notes-only view; link scope starts fail-closed at invite-only and may expand only to workspace/team/anyone-with-link when workspace policy permits.
- For `external_sensitive` or `regulated_record` profiles, external/client/legal
  creation first shows the exact pinned revision and records the required human
  review receipt. The receipt is also bound to the projection-policy version,
  approved audience, intended egress purpose, recipient-or-link scope and
  capability class. A receipt for another revision, root bundle, recipient,
  scope/capability, policy version or reviewer scope is stale and cannot
  authorize egress; ordinary on-screen reading remains approval-free.
- A review receipt belongs to one egress intent. Artifact creation atomically
  revalidates and consumes it while pinning the exact type/revision and receipt
  digest; expiry, revocation or changed access/policy/deletion epoch creates no
  artifact and requires a new review.
- Existing links/artifacts have explicit expiration/revocation/deletion behavior and never follow a later refresh silently.
- Submission uses a stable idempotency key. The first click immediately enters one pending state; duplicate clicks and reloads cannot create another link/artifact.
- Navigating away does not fabricate cancellation. On return, GRAF resolves pending, success, failed or ambiguous creation from authoritative state.
- Proven pre-create failure may be retried safely. Ambiguous creation is reconciled before any retry; the UI never asks the user to risk a duplicate.
- Success confirms recipient/link, permission, exact type/revision and next action. Failure preserves the meeting/result and explains what remains safe.
- An optional follow-up message is a clearly labelled draft assembled
  deterministically from already verified visible decisions, actions and open
  questions using versioned static labels/order. It adds no agreement and
  requires an explicit separate send action outside this generation flow. Any
  later model rewrite/personalization is a separate versioned and verified phase,
  never hidden work in this flow.
  If the draft budget cannot include every critical visible decision/action, the
  draft is unavailable with a link back to full notes rather than silently
  incomplete.

## 7. Custom format

- The catalog separates built-in and personal formats. Built-ins are view-only and may be duplicated or set as default; duplication creates a personal copy. Personal formats may additionally be deleted.
- `Новый формат` creates an autosaved draft with a visible `Сохранено`/`Сохраняем`/error state; it never creates multiple drafts from repeated clicks.
- User creates a type from supported blocks, name, icon and purpose.
- Preview explains expected sections and exclusions; it does not run arbitrary user prompt instructions.
- Edit creates a new template version under the same stable type.
- Existing results remain readable after a format is retired/deleted; they show an archived-format state. Future ensure/refresh/default selection is unavailable until the user duplicates or chooses an available format.
- Catalog search/filter/order and available/unavailable states are deterministic. Duplicate, set-default and delete have explicit results; permanent delete requires confirmation and does not remove historical meeting results.
- Generation failure from a personal format restores the last ready result and identifies the failed type without raw provider errors.

## 8. Feedback

- Feedback is optional and non-blocking.
- User can flag a whole result or exact claim: wrong fact, missed item, wrong owner/date, duplicate, wrong type fit, too long/short, useful.
- Feedback never auto-changes the result or production prompt.

## 9. Global action follow-through

Owned by Feature 206 and not a release blocker for the core summary journey. Feature 205 owns the mutable action ledger and the single shared command path used here and inside meeting detail.

- The global view projects the same canonical task IDs used inside meetings.
- Completing or editing a task in either view is immediately consistent in the other view.
- Filters include open/completed, assignee, due date and source meeting; unavailable plans/permissions show a truthful state rather than an empty list.
- Opening a task returns to its exact meeting, summary type and evidence when available.

## 10. Optional continuity with a previous meeting

- When an authorized previous meeting in the same series/project is available,
  GRAF may show closed, carried-over, overdue, changed, new and removed items.
- The section identifies both meetings and keeps separate evidence links.
- It uses canonical decision/action identities and the mutable action ledger;
  it does not infer completion from a prose summary.
- Missing, deleted or inaccessible previous context hides the section or shows
  one truthful unavailable state without blocking the current summary.
- External previous minutes are context only and can never mutate tasks or
  override the current meeting.

## 11. Optional subject-scoped generated outcome

Owned only by Feature 208 and not a blocker for the shared Summary Workspace.
It is not the zero-inference `my_actions` filter owned by Features 205/196.

- Entry exists only for an approved product purpose with explicit audience and
  consent policy. A shared summary type, personal default, participant name or
  `my_actions` selection never triggers subject-scoped generation implicitly.
- Before work starts, the UI names the private audience and purpose without
  exposing another participant or confirming hidden subject-scoped content.
  The request binds the authenticated user, trusted participant-mapping
  snapshot and current access-policy epoch.
- The result uses a separate subject-scoped slot/receipt contract. It never
  reads, writes, aliases, becomes default for or falls back to a shared Feature
  183 meeting/type slot; shared Receipt V1 cannot represent it.
- Another viewer, a changed mapping, revoked consent, access loss or deletion
  fails closed. A prior shared result remains unchanged and is never repainted
  as the private result or vice versa.
- New share/export is disabled by default. Any later egress requires its own
  explicit subject/audience/purpose-bound review receipt and cannot promote the
  result to the meeting default.
- Preparing, failed, unavailable and revoked states preserve the shared meeting
  context and expose only safe private-scope recovery. Browser and embedded
  macOS may expose this route only after the separate Feature 208 Spec Kit,
  privacy, calibration and cross-viewer tests pass.

## 12. Edit note blocks and comment

Owned by Feature 209. The generated summary revision remains immutable; the
editable surface is a separate document revision pinned to its source
`outcome_set_id`.

- The observed block menu exposes color, copy, duplicate, comment and delete
  only after each command has a real authorized lifecycle; no visual-only menu.
- Human edits, duplication, ordering, color and deletion change the document
  projection, never canonical claims/evidence, the generated receipt or prompt
  feedback. Every block visibly preserves generated versus human provenance.
- Comments bind an exact document/block revision and follow the permission
  granted by Feature 203. Concurrent edits use expected version and preserve
  the last authoritative document on conflict/offline ambiguity.
- A summary refresh creates a new generated result and never silently overwrites
  an edited document. Rebase/reset/replacement is a separate explicit document
  command with preview and recoverable history, not routine candidate approval.

## 13. Ask the grounded meeting assistant

Owned by Feature 210. The Krisp-like bottom-right host and contextual suggestions
appear only after the complete assistant contract is available.

- Typing a question or choosing a suggested prompt is one explicit intent; merely
  opening a meeting, result or suggestion starts no inference.
- Each answer pins the authorized meeting, canonical source, selected result
  context, prompt/root/calibration binding and authenticated subject. Transcript
  and note content remain data, never instructions.
- Answers are query-focused and evidence-backed. Unsupported answers say that
  the meeting does not establish the requested fact; general world knowledge is
  not silently mixed into meeting truth.
- Leaving/reloading preserves one durable request; ambiguous egress is wait-only.
  The assistant never changes a summary slot, task, transcript or prompt label.

## 14. Correct transcript text or speaker attribution

Owned by Feature 211. The observed transcript-row edit/delete controls remain
absent until this revision lifecycle exists.

- An edit, speaker correction or segment exclusion creates a new immutable
  transcript/canonical-source revision with actor, timestamp and audit reason;
  accepted media and prior transcript revisions are not mutated in place.
- Commands are authorized, idempotent and expected-version guarded. Conflict,
  offline and ambiguous states preserve the old readable source.
- Confirmed source replacement marks every active saved old-source summary stale
  and coalesces the Feature 197 regeneration fan-out; unsaved and retired types
  are not generated.
- Undo/restoration moves through an explicit revision command and the same source
  fences. Browser and embedded macOS expose equivalent keyboard-accessible
  controls rather than hover-only actions.

## State ownership

| State | Owner | User impact |
|---|---|---|
| Transcript/source readiness | processing workflow | honest meeting status |
| Type current revision | per-type publication slot | saved result |
| Generation progress/error | generation attempt | secondary status |
| Selected type | user presentation preference | no global meeting mutation |
| Last primary view | user+meeting presentation preference | each meeting resumes independently |
| In-progress selected type | durable generation attempt plus transient presentation intent | reload resumes work without replacing the last successful type |
| Prompt/model bundle | deployment operator | invisible except provenance/support |
| Notes output language | Feature 198 profile/generation policy outside the Krisp top-strip reference | remains distinct from transcript language; Feature 196 exposes no `Язык итогов` control in the observed strip |
| Transcript language | transcription workflow | the visible `RU` popover selects a language, requires explicit `Regenerate`, warns up to 30 minutes and may replace the canonical source; it never acts as a summary display toggle |
| Feedback | exact user/outcome/bundle ledger | optional signal |
| Action completion/assignee/due | Feature 205 canonical mutable action ledger | consistent meeting and Feature 206 global projections |
| Subject-scoped generated result | Feature 208 separate authenticated-subject slot/receipt | private optional result; never a shared slot, default or `my_actions` filter |
| Editable note document/comments | Feature 209 document/block revision ledger | human-authored overlay pinned to a generated revision; canonical result remains immutable |
| Grounded meeting assistant | Feature 210 query/session/call/receipt lifecycle | explicit evidence-backed answers; no slot/task/source mutation |
| Transcript correction | Feature 211 transcript/canonical-source revision lifecycle | audited source replacement that stales affected saved summaries |

## CX rules

- Ask the user only for intent that cannot be safely inferred: selecting a different type, explicit refresh, share/export, custom format definition.
- Do not ask the user to quality-control every normal generation.
- Preserve work and context during every failure.
- Restore the last ready type after a failed missing-type generation only while that request owns the latest presentation intent; after newer selection/navigation, report status without moving the user.
- Explain what is happening, what remains safe, and the next useful action.
- Never expose internal candidate, retry-count or provider terminology as the primary mental model.
- Never overload transcript language, notes output-language policy, generation
  state, source state or catalog availability; `RU` always names transcript
  regeneration and each control/message names the affected layer.
- Never overload a shared result, zero-inference `my_actions` filtering and a
  Feature 208 subject-scoped generated result; private generation is always an
  explicit separately authorized intent.
- Never present Feature 209 document edits as regenerated AI truth, Feature 210
  answers as accepted meeting decisions, or Feature 211 corrections as in-place
  mutation of the old source.
- User copy is calm and action-oriented: `Итоги временно недоступны`, `Предыдущая версия сохранена`, `Обновим позже`. Provider, validator and retry reason codes remain internal.
- `Повторить` appears only for proven safe retry; ambiguous egress projects `wait` and never asks the user to trigger duplicate inference.
