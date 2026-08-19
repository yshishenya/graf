# UI Contract: Одна колонка настроек

## Settings mode

- Outer cabinet sidebar is the only settings navigation landmark.
- No hidden legacy settings navigation markup is emitted.
- Overview, form, calendar and billing content occupy column 1.
- Only existing cabinet main padding separates sidebar and content.
- Content retains its current maximum readable width and does not overflow.

## Fallback mode — superseded by Feature 174

- Standalone inner settings navigation is no longer a supported production
  contract. The outer cabinet sidebar is the only settings navigation owner.

## Preservation

- Routes, active-state semantics, forms, CSRF/auth/role gates and native
  recording handoff are unchanged.
- No JavaScript state, listener, storage, router, breakpoint or dependency.
