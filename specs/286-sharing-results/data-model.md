# Data model — F286

All new tenant-owned tables: workspace_id, indexed relationships, RLS enforced for actual runtime roles via existing migration helpers; migrations never enable automatic sending/publication.

## PublishedMeetingSummary

UUID identity, workspace/meeting, source outcome UUID + template_key, schema version, allowlisted projection JSON, publication timestamps. Only supported schema reads; fixed body/label/date survive default-format change. Deletion removes projection. Public success/preview serialize same allowlist; no source URLs/transcript/raw roster.

## Existing grant/invitation additions

Grant ciphertext for recoverable current link and published_summary_id. Invitation published_summary_id and read_expires_at; Первое принятие может создать summary-only право; повторные передачи сохраняют независимые прежние права и читают точную публикацию через принятую адресную отправку с собственным сроком. Old nullable rows retain semantics. Current live link unique index reused; stale/expired/revoked cannot be revived by copy. Updates/rotation require expected identity/version; no anonymous write.

## SummaryDeliveryBatch / SummaryRecipientDelivery

Batch UUID, workspace/meeting/owner, snapshot UUID, idempotency_key unique per owner/workspace, created/scheduled/deadline, automatic/rule version, state. Recipient unique batch+normalized email hash; encrypted email, optional user/invitation/grant, state pending/sending/accepted/failed/unknown/suppressed/cancelled, attempts/failure code/provider ID when available, собственный read_expires_at (30 дней от первой reservation, повтор не продлевает). Hash/identity only in operational events, no emails/tokens/text. Capture recipient list and snapshot atomically. Cancellation never overwrites accepted/unknown as cancelled; attempts reserved at sending are allowed to finish.

## SummarySharingPreference / SummaryAutoSendRule

Preference unique workspace+owner: ask_enabled default true, paused default false, version, auto_epoch and last_resumed_at. ASK changes only version; pause/resume advance auto_epoch so old scheduled batches cannot resurrect. last_resumed_at исключает готовые во время паузы итоги и встречи, начавшиеся до возобновления, из восстановления старых правил. Явное новое правило конкретной встречи, включённое после возобновления до готовности, допускает такую встречу; старое правило и серия накопившиеся встречи не отправляют. Rule workspace+owner+scope+exact target, approved user IDs/email hashes, template, enabled_at, disabled_at/version. Meeting exception suppresses one instance. Series uses existing versioned series_key exact source/calendar/provider. Stable identities, never participant row IDs. Owner/distributor conflict stops AUTO. auto_occurrence_key unique within workspace across owners/versions/status prevents duplicate initial sends. Meeting exceptions retain sticky requires_review/cancel even if roster later returns; only explicit owner reapproval clears review.

## SummaryEmailSuppression

Normalized address hash+sender+workspace unique; opted-out timestamp, signed action token scoped to this preference. No access mutation. Address encrypted only as needed for delivery; no transcript. GET does not mutate; POST is explicit, idempotent.

## State rules

ASK is presentation only. Schedule only after complete publish plus approved eligible rule; grant activation at dispatch, not scheduling. Before every pending recipient reservation: current source/readability/deletion, owner authority, actual membership/email, pause/exception/opt-out, roster/version match, freshness (supported complete Google snapshot <=15 minutes, organizer.self) and ready_at+24h deadline. A changed/private/incomplete event returns entire job to requires_review. Unknown outcomes never automatically repeat. Retry only known failed recipient within same immutable batch; cancellation/expiry checks still apply. Enable/resume affects future instances; no retroactive queued resurrection.
