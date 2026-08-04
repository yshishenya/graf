# Data Model: meeting-outcome-value

Новых таблиц и migration не требуется. Feature связывает существующие сущности
и усиливает их invariants.

## Existing entities

### Meeting / Workspace

- `Meeting.current_outcome_set_id` — единственный authoritative accepted pointer.
- `Meeting.created_by_user_id` — owner actor для policy-owned automatic candidate.
- `Workspace.default_summary_template_key/version` — только active built-in
  default; invalid value закрывается truthful policy state, без silent prompt
  substitution.
- `deletion_epoch` и lifecycle state остаются fence для generation/accept/share.

### ProcessingResult / transcript provenance

- `ProcessingResult` закрепляет imported source revision/hash.
- `TranscriptSegment` даёт canonical id, sequence, time, source role и text.
- `DiarizationSegment` и `MeetingSpeakerName` дают стабильную подтверждённую
  speaker identity. При отсутствии надёжного соответствия model получает
  `UNKNOWN`, а не сгенерированного `Speaker N`.

### MeetingOutcomeGenerationAttempt / DispatchIntent

Automatic identity включает meeting, exact processing result/source hash,
default template version, generator config и actor=`system`. Повторный import,
reload или reconciliation возвращает существующую попытку и intent.

```text
queued → generating → candidate → accepted
                    ↘ rejected | expired | stale
queued/generating → blocked_dependency | failed | ambiguous
```

Ни одно состояние до `accepted` не меняет `current_outcome_set_id`.

### MeetingOutcomeSet / MeetingOutcomeItem

- AI set сохраняет стабильный `generator_version`, а candidate UUID остаётся в
  собственном поле.
- `owner_text` и `due_date_text` допустимы только для `action_items`.
- Каждый available item содержит 1..8 unique refs.
- Stored ref использует существующий JSON field и canonical enrichment:

```json
{
  "transcript_segment_id": "uuid",
  "sequence": 12,
  "evidence_kind": "segment",
  "start_seconds": 42.5,
  "end_seconds": 49.1,
  "source_role": "incoming"
}
```

Model schema по-прежнему разрешает только id+sequence. Time/source role
добавляются server-side из pinned transcript и не доверяются model output.

## Derived projections

- Owner candidate preview: localized category, text, optional owner/due,
  structured source destination; `private, no-store`.
- Accepted owner/full-viewer: existing compact renderer.
- Summary-only: тот же разрешённый read-only outcome projection без transcript
  content, owner-only candidate или JSON dead-end.
- Meeting list: отдельные derived readiness labels для transcript и accepted
  outcome; unknown/failed не маппятся в optimistic «Готово».

## Invariants

1. Один automatic attempt и один dispatch intent на durable source identity.
2. Provider/network call не выполняется в processing import transaction.
3. Candidate content owner-only до accept; share/export читают accepted pointer.
4. Ref существует в exact pinned source, sequence совпадает, duplicates/empty
   rejected.
5. Timestamp/source role всегда вычислены сервером из того же pinned source.
6. Stale/deleted/access-revoked candidate нельзя preview/accept.
7. Prompt/config/schema/model versions pin до egress; production label mutation
   проходит operator gate.
