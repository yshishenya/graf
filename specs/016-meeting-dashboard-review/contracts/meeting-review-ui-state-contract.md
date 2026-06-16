# Contract: Meeting Review UI States

Feature: `016-meeting-dashboard-review`
Date: 2026-06-16

## Information Architecture

The 016 review surface uses two stable top-level modes:

- `Notes`
- `Recording & Transcript`

`Notes` may show unavailable/processing/generation-future states. It must not
invent generated notes or action items when no accepted generation result
exists.

`Recording & Transcript` is the primary value surface for 016. It must show
transcript segments, timestamps, speaker labels, source-role truth, playback
context, and speaker/timeline affordances when content is available.

## Meeting List Controls

Required visible or menu-backed controls:

- Search.
- Status/source/date/access/person/tag filters as available.
- Sort by updated/date/duration where data supports it.
- `New` entry point reserved for upload/recording future flows.
- Row-level future slots for star/save, tag, access/collaboration, and more.

016 behavior:

- Search/filter/sort may operate locally on returned rows or via query
  parameters.
- Future slots are disabled/planned/no-op unless backed by accepted behavior.
- `New` must not start native recording from the web cabinet.

## Detail Header Controls

Required stable locations:

- Meeting title/date/duration/status.
- Source/provenance.
- Speaker review entry.
- Summary/template slot.
- Share/export/delete/more governance area.

016 behavior:

- Share/export/download/delete controls are gated and non-mutating.
- Template and assistant controls are reserved or disabled.
- Speaker correction may be reserved while labels/timeline are readable.

## Processing And Degraded States

| State | Required UI Truth |
|---|---|
| `local_only` | Explain desktop/local upload truth and offer desktop queue/status handoff. |
| `submitted` | Explain server accepted the meeting and processing has not produced content yet. |
| `processing` | Show processing/waiting state and disable transcript-only actions. |
| `ready` | Show transcript, speaker labels/timeline, provenance, and playback shell if allowed. |
| `partial` | Show available content and visible degraded reason for missing pieces. |
| `blocked` | Show safe reason and non-content-bearing recovery guidance. |
| `failed` | Show failure truth and future retry/contact path without changing upload truth. |
| `unavailable` | Show bounded unavailable state without confirming foreign content. |

## Accessibility And Localization

- Russian text must not overflow buttons, chips, table rows, or side panels.
- Controls must have keyboard focus states and accessible names.
- Status meaning must not rely on color alone.
- Icons require either familiar symbols or accessible labels/tooltips.
- Layout must work at desktop browser width and compact embedded desktop width.

## Evidence Rules

Validation screenshots may use sanitized sample data or private local reference
folders. Tracked evidence must not contain:

- real private transcript text;
- email addresses or private account identifiers;
- secrets, credentials, tokens, signed URLs;
- raw audio or live local paths.

## Clean-Room Rules

Allowed from Krisp/Crisp references:

- information architecture patterns;
- density/scanning lessons;
- state coverage;
- interaction affordance categories.

Not allowed:

- copied brand assets;
- copied proprietary copy;
- copied iconography or visual expression;
- copied model behavior;
- copying private meeting data into product fixtures.
