# Admin UX Checklist: 092 Automatic Meeting Detection

**Date**: 2026-07-08

## Review Queue

- [x] Admin surface is specified as `/admin/meeting-detection`.
- [x] It shows VKS candidates, known target health, and registry drafts.
- [x] Candidate cards show safe identifiers, score, reason codes, counts, buckets,
  and reporting installation/workspace counts.
- [x] Candidate cards explicitly exclude raw logs, meeting URLs, passcodes, window
  titles, calendar titles, attendee emails, audio, transcripts, app paths, and
  home paths.
- [x] Review actions include non-target, merge, diagnostic-only draft, validation
  request, prompt review, publish, and disable.

## Product Control

- [x] Adding a candidate from admin starts as `diagnostic_only`.
- [x] Publishing registry is separate from reviewing a candidate.
- [x] Prompt-enabled support requires QA evidence and reviewed registry change.
- [x] Non-target action creates a suppression rule for future clients.
- [x] Every admin action is audited.

## Existing UI Constraints

- [x] Admin review uses existing Jinja/admin/static asset patterns.
- [x] No new frontend framework or build pipeline is required.
- [x] Russian-language admin copy is required by repository issue/admin policy.
- [x] Brand-distance and clean-room constraints are preserved.

## Implementation Validation Requirements

- [x] Requirements specify compact admin layout validation for text/control
  overlap.
- [x] Requirements specify keyboard and screen-reader label requirements for
  review actions.
- [x] Requirements specify CSRF protection requirements for unsafe admin review
  actions.
