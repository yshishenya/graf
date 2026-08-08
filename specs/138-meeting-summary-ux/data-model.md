# Data Model: meeting-summary-ux

## Решение

Новая схема данных не нужна. Feature является presentation slice поверх
существующего `MeetingReviewResponse.notes_action_truth`.

## Используемые поля

- `NotesActionTruthState.source_basis`: provenance summary-блока.
- `NotesActionCategoryState.state`, `label`, `reason`, `items`: truthful
  category state и bounded copy.
- `OutcomeItemView.text`: сохранённая формулировка результата.
- `OutcomeItemView.owner_text`: optional owner, только если он уже inferable и
  сохранён валидатором outcome.
- `OutcomeItemView.due_date_text`: optional due date, с тем же ограничением.
- `OutcomeItemView.truth_label`: сохранённая классификация доверия.
- `OutcomeItemView.source_refs`: pinned segment references; UI не меняет их.

## Invariants

- UI не делает database write и не создаёт новый outcome item.
- `owner_text`/`due_date_text` не заполняются из свободного текста на клиенте.
- Для non-available category items не считаются displayable content.
- Access, deletion, revision и server-mediated egress fences остаются на
  существующих API/view-model границах.
