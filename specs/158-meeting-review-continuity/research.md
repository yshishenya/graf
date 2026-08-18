# Research: Meeting Review Continuity

**Date**: 2026-08-17

## Decisions

### 1. Use a bounded native resize separator

- **Decision**: Keep the current `96px` default as the minimum, expose a horizontal resize separator only when rows overflow, and constrain its maximum to `min(natural row height, available viewport height)`. Use pointer dragging plus ArrowUp/ArrowDown/Home/End keyboard actions. Keep inner scrolling only when the viewport is the limiting constraint.
- **Rationale**: This preserves the current layout for small meetings while making the hidden-row problem discoverable. A native semantic separator expresses a resizable boundary without introducing a slider abstraction or a new dependency.
- **Alternatives considered**: A free-form CSS `resize` handle does not provide a reliable keyboard equivalent or a natural-height ceiling; persisting the height would add state without a requested user benefit; a second scrolling pane would compete with the fixed player.

### 2. Teach lane interaction with a permanent, compact affordance

- **Decision**: When playable audio and at least one speaker lane exist, render a short visible hint next to the lanes and retain the existing action-oriented accessible name. Use cursor, focus, and pressed styles as secondary confirmation. Do not add a modal tour or analytics.
- **Rationale**: The hint works before hover and on touch devices, while the existing keyboard activation remains the same seek action. The copy describes the user's outcome rather than a copied competitor label.
- **Alternatives considered**: Hover-only tooltips fail on touch and do not teach a new user before the first pointer movement; modal onboarding is disproportionate to one interaction; adding a new onboarding system would violate the requested scope.

### 3. Preserve the current audio element during speaker rename

- **Decision**: Treat the successful server-rendered response as a source of canonical speaker labels, update only the matching labels and form value in the existing DOM, and keep the existing audio element and playback listeners untouched. Continue to use the existing authorization/access recovery helper for responses that prove session or access loss.
- **Rationale**: The root cause is the unconditional full-page reload in the shared rename form handler. An in-place label update is the smallest root-cause fix and works for browser and embedded surfaces because they share the form and static asset.
- **Alternatives considered**: Replacing the entire meeting fragment risks replacing the audio element and resetting playback; adding a second audio element or a separate event-listener path would create synchronization bugs; changing the server route to return a new client-specific protocol is unnecessary for this local UI fix.

### 4. Make only the tab strip sticky

- **Decision**: Add a compact sticky class to the existing recording/outcomes tablist, use the current scroll container, give it an opaque background and a zero/default shell offset, and add scroll margins to transcript/outcome targets. Keep the page title, actions, and playback bar out of the sticky area.
- **Rationale**: The main review already owns vertical scrolling and the tablist already owns selection/hash semantics. Reusing it avoids duplicate headers and preserves deep links and source jumps.
- **Alternatives considered**: Making the whole top line sticky consumes too much viewport and duplicates the player context; a JS scroll spy would add state and listeners for behavior CSS already provides; a new router would be out of scope.

## Clean-room UX scan

Public materials were reviewed for interaction principles, not copied text, layout, iconography, or visual treatment. Product UIs that require an account were not treated as inspectable evidence.

| Source | Public observation on 2026-08-17 | Principle applied to GRAF |
|---|---|---|
| [W3C ARIA APG Slider Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/slider/) | A keyboard-operable range needs an explicit focus model and predictable increment/decrement behavior. | Give the resize boundary an explicit focus target, bounded values, and deterministic keyboard steps. |
| [MDN separator role](https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Roles/separator_role) | A focusable, adjustable separator communicates a boundary whose position can be changed; `aria-valuemin`, `aria-valuemax`, and `aria-valuenow` expose the range. | Use a semantic horizontal separator for the timeline boundary instead of an unlabelled visual grip. |
| [Krisp AI meeting notes](https://krisp.ai/ai-meeting-notes) | Public positioning connects transcripts, speaker context, and actionable notes in one review workflow. | Keep the timeline hint close to the review action and preserve source-linked playback rather than adding a separate tutorial. |
| [Fathom AI meeting assistant](https://www.fathom.video/ai-meeting-assistant) | Public materials emphasize searchable recordings, transcripts, and highlights as one review surface. | Make the playback relationship explicit at the point of interaction and keep navigation available during long content. |
| [Otter meeting transcription](https://otter.ai/meeting-transcription) | Public materials emphasize speaker identification and readable transcript review. | Never allow the expanded lane to clip names or controls; use complete rows as the natural height unit. |
| [Fireflies meeting assistant](https://fireflies.ai/) | Public materials combine transcript, search, and meeting insights rather than hiding review actions behind onboarding. | Prefer a small always-visible cue over a modal onboarding flow. |
| [tl;dv meeting recorder](https://tldv.io/) | Public materials emphasize jumping through recorded meeting moments and sharing review context. | Keep lane activation and source jumps as direct, one-action playback navigation. |

## Current GRAF baseline and root causes

- `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css` caps `.speaker-timeline` at `max-height: 96px` with internal scrolling and has no resize control.
- `apps/server/src/twobrain_rec_server/cabinet/rendering.py` emits keyboard-operable lane tracks but no persistent interaction hint.
- `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js` handles lane click/Enter/Space, but the speaker rename handler calls `window.location.reload()` after every successful response.
- `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_detail_content.html` renders the existing tablist as ordinary flow content, so it leaves the viewport during long transcript/outcome reads.
- Browser and embedded meeting detail use the same template and cabinet static assets, so one shared implementation is sufficient for parity.

## Validation assumptions

- Synthetic server-rendered fixtures are sufficient for contract and focused regression checks; no real meeting content is required.
- Manual visual review must cover light/dark, narrow embedded, keyboard focus, and reduced-motion states using the product's browser/native tools.
- No new analytics, storage, dependency, API, or persistence contract is needed for this slice.
