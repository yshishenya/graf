# Contract: Clean-Room Reference Comparison

Date: 2026-06-16

## Purpose

034 must keep comparing the implementation with final mockups and Krisp
desktop/web reference while preserving clean-room distance. This contract
defines what may be recorded and what blocks acceptance.

## Allowed Reference Content

The comparison may record:

- information architecture categories;
- high-level user journey patterns;
- relative surface ownership, such as native capture vs web review;
- density lessons such as meeting list first, status-rich rows, and detail
  review workspace;
- generic interaction categories such as search, filter, sort, share, export,
  delete, transcript, playback, and assistant scope;
- differences where 2brain intentionally diverges.

## Forbidden Reference Content

The comparison must not record or copy:

- Krisp logos, brand colors, icons, illustrations, animations, exact component
  shapes, or proprietary assets;
- exact Krisp UI copy or strings beyond short category labels needed for audit
  context;
- private meeting titles, account names, emails, transcripts, participants, or
  screenshots;
- pixel-level layout matching or visual reconstruction;
- proprietary feature behavior beyond category-level observation;
- raw browser/app screenshots from Krisp unless separately sanitized and
  approved for commit.

## Required Comparison Surfaces

At minimum, compare these surfaces when evidence exists:

- desktop first viewport;
- desktop embedded meeting list;
- desktop embedded meeting detail;
- web meeting list;
- web meeting detail;
- governance actions: share, export/download, deletion/retention;
- unavailable/auth/degraded states.

## Required Result Fields

Each comparison record must include:

- surface;
- allowed lessons used;
- implementation alignment;
- intentional differences;
- forbidden similarity result;
- evidence references;
- result: `pass`, `needs_polish`, or `blocked`.

## Blocking Conditions

The comparison is blocked if:

- committed evidence contains private Krisp content;
- implementation copies exact Krisp visual expression or copy;
- desktop first viewport remains diagnostics-first without a clear launch gap;
- review/governance surfaces are not discoverable and no blocker is recorded;
- reference alignment is claimed without evidence.
