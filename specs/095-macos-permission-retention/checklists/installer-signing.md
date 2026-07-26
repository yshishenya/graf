# Installer And Signing Checklist: macOS Permission Retention

> Historical local-fixture checklist. Current public releases must use the
> Developer ID-only gates in Feature 130; local/self-signed and ad-hoc checks
> below are not release acceptance.

**Purpose**: Validate requirements quality for local signing, installer
packaging, release boundaries, and parked driver scope.
**Created**: 2026-07-09
**Feature**: [spec.md](../spec.md)

## Signing Completeness

- [x] Are ad-hoc, local self-signed, Apple Development, Developer ID
  Application, and unknown signature states distinguished?
- [x] Is local self-signed signing explicitly accepted only for local
  owner-machine validation?
- [x] Does the spec require stable designated requirement evidence rather than
  trusting the identity display name alone?
- [x] Does the spec require failure on signing drift?
- [x] Are certificates, private keys, passwords, and generated signed packages
  excluded from git and evidence?

## Installer Boundary

- [x] Does the spec keep the default local installer desktop-app-only?
- [x] Is package-level unsigned local validation distinguished from app bundle
  signing?
- [x] Does the spec require install/reinstall validation from
  `/Applications/GRAF.app`?
- [x] Does the spec avoid changing install behavior for active recordings
  without a separate capture-safety decision?

## Release Boundary

- [x] Are Apple Developer account, Developer ID Application certificate,
  Developer ID Installer certificate, notarization, stapling, and public
  Gatekeeper validation explicitly deferred?
- [x] Does the changelog/status wording requirement avoid claiming production
  release readiness?
- [x] Is there no production deploy gate in this slice?

## Parked Driver Boundary

- [x] Is HAL driver install excluded from permission-retention acceptance?
- [x] Is CoreAudio restart excluded from normal validation?
- [x] Would any future driver/package change require a separate spec or explicit
  task?

## Notes

Checklist pass complete. The key implementation question is whether
`build-local-installer.sh` accepts local self-signed app signing only behind an
explicit local validation flag while preserving stricter default release-like
behavior.
