# Data Model: Боковая навигация настроек

This feature has no persisted data model and requires no migration.

## Presentation entity

`SettingsCategoryView` remains the server-side projection used by the Jinja
navigation macro:

| Field | Meaning | Invariant |
| --- | --- | --- |
| `id` | Canonical category key | One of the six existing route-map keys |
| `label` | Safe Russian display name | Server-defined, never user-provided |
| `description` | Overview helper copy | Server-defined |
| `scope_label` | Area affected by the setting | Empty only for overview; does not define grouping |
| `href` | Browser or embedded route | Built from explicit server suffixes |
| `group_label` | Visible presentation group | Server-defined; no auth or route meaning |

## Group order

The model emits groups in this order:

1. `Основное`: overview
2. `Встречи`: recording, summaries, calendar
3. `Пространство`: workspace
4. `Аккаунт`: account

The order is part of the UI contract. A group label is not a link, permission,
scope, or persisted preference.

## Safety invariants

- Browser and embedded models differ only by the existing base path.
- No request/query value can create a category, group or href.
- Sensitive provider/device fields are not members of this projection.
- The active item is selected by the already validated `active` category passed
  by the renderer; the template does not interpret arbitrary paths.
