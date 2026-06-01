# Stale Browser Device-ID Recovery

## Purpose

Record what happens when a browser keeps a stale selected `2brain Rec` device ID
after `coreaudiod` restart, repair, update, or device re-publication.

## Steps

- [ ] Select `2brain Rec Microphone` and `2brain Rec Speaker` in the browser
  target settings.
- [ ] Restart `coreaudiod` or reinstall/repair the driver.
- [ ] Reopen the browser target audio settings.
- [ ] Record whether the selected devices are still valid, stale, missing, or
  require user reselection.
- [ ] Record whether 2brain Rec UI shows ready only after fresh route evidence.

## Evidence Rules

- Skipped browsers are `not_accepted`.
- Stale selected IDs without safe recovery are `blocked`.
- Device visibility alone is not live-route acceptance.
