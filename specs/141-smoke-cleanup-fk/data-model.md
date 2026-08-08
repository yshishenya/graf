# Data Model: Надёжная очистка production smoke-данных

## Existing entities

| Entity | Relevant relationship | Cleanup rule |
|---|---|---|
| Smoke identity | organization → workspace → user/device → run id | Scope discovery and identity cleanup remain unchanged. |
| Meeting | belongs to smoke workspace/user/device | Only discovered smoke meetings are eligible. |
| MediaRevision | belongs to meeting and workspace | Delete after every child row linked by meeting or revision is removed. |
| Revision-linked child rows | may carry both meeting_id and media_revision_id | Match the smoke meeting or a revision selected from that meeting. |
| Storage objects | live under organization/workspace smoke prefix | Remove only that prefix and report residue. |

## Invariants

- No production schema or foreign-key constraint changes.
- A revision-linked child row cannot survive deletion of its selected smoke
  media revision.
- A cleanup rerun over an already-clean identity is a no-op with no residue.
- A row outside the selected smoke identity is never eligible solely because it
  shares a workspace or revision-like value.
