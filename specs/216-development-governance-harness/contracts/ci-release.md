# Contract: SHA-bound CI and Release Train

## CI lanes

- `focused`: local changed-path checks while implementing.
- `fast`: PR-ready feedback; may be repeated for new SHAs.
- `full`: one authoritative run for an immutable release candidate; diagnostic
  broad runs receive a distinct non-release identity.

## Run identity

Every run records requested SHA before execution and observed SHA immediately
before publishing evidence. A mismatch yields `stale` or `cancelled`.

## Candidate freeze

Freeze records source SHA, included Feature IDs, changelog digest and candidate
ID before Full CI. Any subsequent change invalidates the candidate. Exactly one
authoritative Full CI result may be attached to a candidate.

## Release output

Successful candidate produces CalVer `vYYYY.MM.DD.N`, matching Git tag, GitHub
Release and Russian notes containing changes, validation evidence,
compatibility/migration impact, known limitations and links. A failed smoke or
rollback gate blocks publication.
