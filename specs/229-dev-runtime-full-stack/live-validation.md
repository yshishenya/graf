# Live validation: presentation lifecycle

Metadata-only operator evidence for T039. No production command, deploy,
migration, data read or release publication is part of this rehearsal.

## Evidence validity

The rehearsal below predates the lifecycle hardening in follow-up PR #6384 and
must not close T039. Its final candidate was `e3d95139d949ea780bc3134a404385ec27cd93d7`,
while the hardened implementation continues in PR #6384. Repeat clean-state
macOS smoke and injected-failure rollback on that PR's final exact SHA before
marking T039 complete.

## Rehearsal baseline

- captured at: `2026-09-02T12:29:38Z`
- known-good Dev SHA: `1d5cef3b9eef3ce517f6a5739b12a8c1774c712c`
- installed process path: `/Applications/GRAF Dev.app/Contents/MacOS/GRAF`
- macOS displayed process name: `GRAF Dev`
- macOS window title: `GRAF Dev`
- live smoke: 13/13 PASS, including `app_identity`, `app_presentation` and
  `exact_source_sha`
- production app CDHash: `bde38a180c557dcb8624de32ad1841163a61439c`
- production `Info.plist` SHA-256:
  `caadd72e8966ec6dd006cbbd799fa95f36a6b2aa30415aa42ed290c58c115840`
- production data file count: `21`
- production data metadata SHA-256:
  `ba56daf0d7d49ec521b50914d3923e0ac4cf819feb58471a4eb621035279df28`

The final section is appended only after the injected failure, compensation,
explicit rollback and post-rehearsal fingerprint comparison complete.

## Fixed-candidate boundary

- captured at: `2026-09-02T13:07:09Z`
- `1d5cef3b9eef3ce517f6a5739b12a8c1774c712c` is retained only as evidence of
  the original presentation fix; repeated restart exposed a successful
  one-shot `rec-minio-init` being treated as a failed Compose wait.
- `1d574db6e8faddb067ec3210f19e623185e60370` contains the shared startup and
  cleanup correction and is the first valid parent for the final rehearsal.
- live smoke on that parent: 13/13 PASS.

## Final rehearsal result

- completed at: `2026-09-02T13:20:41Z`
- final candidate: `e3d95139d949ea780bc3134a404385ec27cd93d7`
- controlled failure: the exact candidate `graf-dev` media-worker container was
  stopped by its Compose/source-SHA labels; promotion failed readiness, kept
  the pointer on `1d574db6e8faddb067ec3210f19e623185e60370` and restored that
  parent to 13/13 live smoke PASS without `compensation failed`
- explicit rollback: `e3d95139d949ea780bc3134a404385ec27cd93d7` to
  `1d574db6e8faddb067ec3210f19e623185e60370`, 13/13 PASS
- final promotion: `e3d95139d949ea780bc3134a404385ec27cd93d7`,
  13/13 PASS; the running process, window, bundle names and channel are
  `GRAF Dev`, `GRAF Dev`, `GRAF Dev` and `dev`; icon key is `AppIcon`
- production app CDHash after:
  `bde38a180c557dcb8624de32ad1841163a61439c`
- production `Info.plist` SHA-256 after:
  `caadd72e8966ec6dd006cbbd799fa95f36a6b2aa30415aa42ed290c58c115840`
- production data content-tree SHA-256 before and after the control cycle:
  `000069efb384312d3f06ecf3db9de07583ea71c8f6fc4603b317adbb2150fda4`
- production data path-and-size SHA-256 before and after the control cycle:
  `69241f4584d76fd4645d5c57a9b1dbae1f46d417b9edf268a9dd21e32d78b7a7`
- production data file count before and after: `21`

The earlier mtime-only digest changed while the production app remained
running, so it was not used as mutation evidence. The stable content-tree and
path/size fingerprints above bound the full final rollback/promotion cycle.
No production deploy, migration, restart or release publication was executed.

## Immutable-image hardening baseline

- captured at: `2026-09-02T17:54:18Z`
- exact implementation SHA: `f208b1b22d08cc63e4d28821ce006e9fd88d37ca`
- GitHub `governance-fast`: PASS, run `33662388294`, exact SHA matched
- candidate manifest: `dev-f208b1b22d08`, with all nine Compose services
  resolved to locally present immutable `sha256:` image IDs
- pre-hardening active manifest `dev-221932bc05ef` lacked the new
  `storage_init` image identity, so it was not used as a rollback target; the
  verified owned `graf-dev` runtime was stopped gracefully without `-v` or
  state/data deletion before the one-time cutover
- promotion and repeated live smoke: 13/13 PASS, including
  `app_identity`, `app_presentation` and `exact_source_sha`
- installed bundle: `GRAF Dev`, bundle ID `pro.2brain.graf.dev`, channel `dev`;
  the rendered `AppIcon.icns` contains the separate yellow `DEV` badge
- production app CDHash remained
  `bde38a180c557dcb8624de32ad1841163a61439c`; production `Info.plist`
  SHA-256 remained
  `caadd72e8966ec6dd006cbbd799fa95f36a6b2aa30415aa42ed290c58c115840`
- production data content-tree SHA-256 remained
  `fe98c4ae3473e073683a00ca754d874991c8e045e3349215eab5b38f6ac5ffd7`;
  file count remained `21`

This establishes the first rollback-capable immutable baseline. T039 remains
open until a second full manifest proves injected-failure compensation,
explicit rollback, final promotion and the post-cycle production fingerprints.

## Final immutable-image rehearsal

- completed at: `2026-09-02T18:07:30Z`
- final implementation SHA: `f208b1b22d08cc63e4d28821ce006e9fd88d37ca`
- evidence-only candidate SHA: `f15a76388b5dfe2c139859dc57b8c7ca482b4959`;
  its only repository change records the already-passed hardened baseline
- GitHub `governance-fast`: PASS on the evidence candidate, run `33664086315`
- controlled failure: candidate `rec-media-worker` container `38209eb554b6`
  was selected by project, service and source-SHA labels and stopped during
  promotion; readiness failed as expected
- compensation: active pointer remained `dev-f208b1b22d08`; all nine actual
  container image IDs matched that manifest and live smoke returned 13/13 PASS
- explicit rollback: successful promotion to `dev-f15a76388b5d`, checkout of
  the exact target SHA, rollback to `dev-f208b1b22d08`, and 13/13 PASS
- final promotion: `dev-f15a76388b5d` active with all nine actual container
  image IDs equal to the selected manifest and final live smoke 13/13 PASS
- installed presentation: display/bundle name `GRAF Dev`, bundle ID
  `pro.2brain.graf.dev`, channel `dev`; `AppIcon.icns` SHA-256 is
  `0bde2fe5463d1632d28dadc0d2cce5c992d401248b51a705fbeca21b02ed2651`
  and visual inspection confirms the separate yellow `DEV` badge
- production app CDHash before and after:
  `bde38a180c557dcb8624de32ad1841163a61439c`
- production `Info.plist` SHA-256 before and after:
  `caadd72e8966ec6dd006cbbd799fa95f36a6b2aa30415aa42ed290c58c115840`
- production data content-tree SHA-256 before and after:
  `fe98c4ae3473e073683a00ca754d874991c8e045e3349215eab5b38f6ac5ffd7`;
  file count before and after: `21`

No production deploy, migration, restart, data reset, state deletion or release
publication was executed. The repository-global Dev state and volumes were
preserved throughout the controlled cycle.
