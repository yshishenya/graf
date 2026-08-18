# Research: Понятная подсказка на таймлайне

## Decision: inline action/result copy

The current phrase names an internal visual concept («дорожка») but does not
tell the user which visible part is interactive or what follows. The proposed
Russian copy is:

> Нажмите на цветной фрагмент, чтобы перейти к этому месту записи.

It follows the compact instruction pattern: action first, object second,
result last. It describes the existing seek behavior truthfully (it does not
promise autoplay), is useful before hover and remains available to keyboard
and touch users.

## Decision: no tooltip-only or first-use dismissal

Native title/tooltips are hover-dependent, not reliable on touch, and do not
replace an accessible name. A dismissible first-use hint needs storage and can
hide the explanation when it is needed again. A low-contrast inline note is
smaller and more robust for this server-rendered surface.

## Decision: keep accessible track label aligned

The existing track control already exposes a keyboard action label and handles
Enter/Space. Tests will assert that it keeps the same meaning as the visible
copy rather than adding a second interaction model.

## Alternatives considered

- «Нажмите на дорожку, чтобы перейти…» — rejected because «дорожка» is
  ambiguous and describes navigation rather than listening.
- A play icon without text — rejected because the icon alone is ambiguous and
  weak for screen readers.
- A large onboarding callout — rejected because it competes with playback and
  violates the requested minimalist treatment.
