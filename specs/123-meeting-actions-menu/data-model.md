# Data Model: Понятное меню действий со встречей

## Persistence Decision

This feature introduces no table, column, cache, stored preference or lifecycle
artifact. It only projects existing meeting, capability and governance truth
into a smaller interaction surface.

## Existing Entities Used

### Meeting Review

Existing server-owned snapshot for the current meeting detail. Relevant fields:

- meeting identity and visible title;
- export availability by content scope;
- audio download capability;
- delete capability and bounded lifecycle truth;
- media revision and provenance status;
- available artifacts;
- calendar context;
- speaker lanes;
- recent access activity.

### Meeting Action

A transient projection derived for the current response:

- stable action kind: `export`, `download_audio`, `details`, `delete`;
- Russian label;
- optional short explanation;
- availability derived from existing server policy/state;
- destination type: existing dialog, existing server download, details dialog,
  or existing delete confirmation;
- destructive state for delete only.

No action availability is stored in the browser or database.

### Menu State

Ephemeral presentation state only:

- `closed` or `open`;
- currently focused available action;
- visible placement adjacent to `Ещё`.

Transitions:

```text
closed --open--> open
open --move focus--> open
open --Escape/outside click--> closed + focus on Ещё
open --select--> closed + existing destination flow
```

### Details Dialog State

Ephemeral presentation state only:

- `closed` or `open`;
- sections included only when present in the existing meeting review;
- return focus target: visible `Ещё` trigger.

## Validation Rules

- Preserve server action order after unavailable actions are removed.
- Never render an empty separator, helper or menu.
- Never derive authorization from menu visibility.
- Never synthesize missing artifacts, policy reasons, activity or provenance.
- Do not alter export revision pinning, deletion lifecycle or audio egress.
