# Future Calendar/Contact Speaker Naming Boundary

**Recorded**: 2026-07-13 (Europe/Moscow)
**Feature boundary**: explicitly excluded from `098-calendar-auto-context-match`
**Requirement trace**: FR-020-FR-023, FR-045; SC-008

## Current 098 Truth

Calendar participants are invited roster metadata only. Feature 098 may show a
bounded roster snapshot beside an authorized meeting, but it does not use that
snapshot as evidence of who actually spoke.

Within 098:

- transcript and diarization labels remain `SPEAKER_XX`;
- participant display names never rename speaker labels;
- participant email presence never creates identity binding;
- participants never create meeting access or share grants;
- participants never become summary, report, message or email recipients;
- matching and recurring continuity never trigger delivery.

## Separate Future Capability

A later calendar/contact-based speaker-name suggestion feature may be proposed
only as a separate specification and implementation slice. It must not be
introduced as an incremental extension of the 098 roster projection.

That future slice requires, at minimum:

1. explicit user consent and a clear owner correction/revert path;
2. a documented confidence model that does not equate invitation with speech;
3. speaker-truth evidence from the recording rather than roster order;
4. handling for rooms, resources, groups, aliases, duplicate contacts and
   people who were invited but absent;
5. privacy-safe identity storage, audit and deletion behavior;
6. independent authorization and no-recipient/no-delivery guarantees;
7. web and embedded UX that labels suggestions as suggestions until confirmed;
8. synthetic and real acceptance evidence before any automatic naming claim.

## Upgrade Trigger

The capability remains deferred until a product owner explicitly opens a new
feature covering consent, confidence, correction and speaker truth. A request
to make calendar names visible in transcript lanes is not sufficient by itself
to cross this boundary.

## 098 Acceptance Rule

Any 098 implementation or test that maps a calendar participant to a
`SPEAKER_XX` label, creates a permission/share row, creates a recipient or sends
content is a regression and blocks feature closeout.
