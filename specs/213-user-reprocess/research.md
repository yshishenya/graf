# Research: повторная обработка записи пользователем

Проверка перед реализацией 2026-08-30: ветка создана от актуального
`origin/master` (`5f448ac9f705c33fb2e731657d46a224dd08013b`). Существующих
`ProcessingWorkflow.workflow_id`, `attempt_ordinal` и
`ProcessingResult.processing_workflow_id` достаточно для predecessor/successor
CAS и выбора полного результата; новая таблица, колонка или миграция не нужны.

## 1. Information architecture

**Decision**: Put `Повторно обработать запись` in the ordinary meeting `Ещё` menu, immediately before deletion, and show it only to the meeting creator.

**Rationale**: The user is fixing their own recording. No administrative file page, operator role or support console is required.

Evidence board: [GRAF: повторная обработка готовой записи](https://www.figma.com/board/BsCTzFSaDybxmlQPQrDF5N). The board's operator/admin frames are superseded by this decision; the confirmation, status and continuity states remain applicable.

## 2. Naming and confirmation

**Decision**: Action `Повторно обработать запись`; confirmation `Запустить повторную обработку`. Do not ask for a reason.

**Rationale**: Reprocessing updates transcript, speakers and outcomes, so `Перезапустить транскрибацию` is too narrow. `Повторить сейчас` remains reserved for waking the same retryable attempt.

## 3. Published result without a new pointer

**Decision**: Do not add `Meeting.current_processing_result_id`. Fix the existing shared `effective_processing_result_query()` so the customer-visible result is the newest complete result by processing-attempt ordinal and result version.

The selector must:

- join `ProcessingWorkflow`;
- apply the existing `complete_processing_result_clause()`;
- stay on the latest accepted media revision;
- order by `ProcessingWorkflow.attempt_ordinal DESC`, then `ProcessingResult.result_version DESC` and existing deterministic tie-breakers.

**Rationale**: Result import already locks the meeting, rejects superseded workflows, checks accepted media revision, source fingerprint and deletion state, and commits the result plus transcript/diarization segments atomically. While a replacement is partial or failed, the previous complete result remains the selector winner. A persistent publication pointer would duplicate this automatic rule and is only needed for future manual approval, rollback or version selection.

## 4. One selector for every customer channel

**Decision**: Separate operational state from customer content everywhere:

- latest workflow/job drives status and retry;
- effective complete result drives transcript, diarization, playback association, share, export, egress and desktop review availability;
- outcomes keep their existing independent published slot and are labelled `По предыдущей версии расшифровки` while their source result differs from the effective result.

**Rationale**: Current readers mix latest workflow, latest imported result and outcome-bound result. A new partial attempt can therefore hide a good transcript or make channels disagree. Reusing one complete-result helper fixes the root cause once.

## 5. Request idempotency without a command table or schema field

**Decision**: The browser sends the `workflow_id` it observed before opening confirmation. Under the existing meeting/workflow locks, that predecessor may create at most its immediate successor. Replays and a second tab return the same successor, including after it has completed; requests older than one successor fail as stale.

**Rationale**: A single request-ID field cannot remember a different ID from a second tab that coalesced into the active attempt. The predecessor/successor CAS uses durable identity already present in status and the database, survives both lost-response cases, and avoids a migration. An `OperatorReprocessCommand` table, actor role snapshot and reason ledger are unnecessary after removing the admin/audit scope.

## 6. Temporal exact attempt identity

**Decision**: Add `processing_workflow_id` to every new Temporal processing payload. Activities and error persistence load that exact row and validate workspace, meeting, revision and Temporal workflow ID. Old histories may omit the field through a temporary compatibility fallback.

**Rationale**: The current activity loads the latest active workflow. A delayed activity from an older execution can otherwise attach to a newer attempt. Adding payload identity does not change Temporal command order; replay tests cover old and new histories.

## 7. Reuse existing execution and recovery

**Decision**: Reuse `ProcessingWorkflow`, `MediaScribeJob`, `start_processing_workflow()`, `GET /processing`, `POST /processing/check`, `schedule_generation`, provider idempotency and unknown-POST reconciliation. Add only one owner endpoint: `POST /api/v1/meetings/{meeting_id}/processing/reprocess`.

Automatic retry and `Повторить сейчас` wake the same workflow/job. A new confirmed reprocess request after terminal completion creates a new workflow and job.

## 8. Authorization and quota

**Decision**: Revalidate `Meeting.created_by_user_id == principal.user_id` on launch and on manual actions for a replacement attempt. Shared recipients cannot launch or retry it. Reuse the revision-scoped quota reservation key, so the same source revision is not charged twice.

## 9. Transcript and outcome publication

**Decision**: The effective transcript changes only when transcript and matching non-empty diarization are complete. Outcome generation follows the new effective result and retains its existing independent CAS. Prior outcomes stay readable with the previous-version label until matching outcomes publish.

## 10. Deliberate exclusions

No admin routes/templates, reasons, operator audit, new scheduler, new queue, new Temporal workflow type, version comparison, rollback UI, provider cancellation, transcoding or MediaScribe/model/post-processing changes.
