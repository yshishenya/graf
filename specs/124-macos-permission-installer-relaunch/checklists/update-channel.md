# Sparkle update-channel checklist

- [x] Bootstrap `GRAF.app` contains the public HTTPS feed and active public key.
- [x] Bootstrap retains `pro.2brain.graf` and the expected local signing
  designated requirement.
- [x] `v2026.07.24.2` is strictly newer than the current public appcast and the
  old `v2026.07.24.1` bootstrap is documented as manual-only.
- [ ] Candidate archive passes safe ZIP, nested-code, checksum and Sparkle
  continuity validation before publication.
- [ ] Protected signing workflow verifies the exact `master` tag, manifest,
  cloud signer and release-operator Keychain attestation.
- [ ] Versioned ZIP/PKG/checksum assets are public and readable before the
  signed appcast replaces the last-good feed.
- [ ] Public appcast and archive pass post-publication HTTPS and signature
  validation; previous artifacts remain available for rollback.
- [ ] Release notes explain the `.1 → .2` manual bootstrap and owner-only trust
  limitation in Russian.
