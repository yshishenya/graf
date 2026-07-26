# Contract: public Developer ID release

## Inputs

- `GRAF_REQUIRE_PUBLIC_UPDATE_TRUST=1` for a public candidate.
- `GRAF_APP_SIGN_IDENTITY` matching `Developer ID Application: ...`.
- `DEVELOPER_ID_INSTALLER_IDENTITY` matching `Developer ID Installer: ...`
  when a `.pkg` is produced.
- exact CalVer `GRAF_VERSION`, public HTTPS feed URL and the active Sparkle
  public manifest when updates are configured.
- previous Developer ID app for update continuity validation.

## Required behavior

1. The builder rejects missing or non-Developer-ID app/package identities and
   rejects ad-hoc/local opt-in flags in public mode.
2. The validator rejects any candidate whose signing kind is not
   `developer-id`.
3. The validator requires hardened runtime, valid notarization staple and
   Gatekeeper acceptance for the public app.
4. Package validation separately requires Developer ID Installer signature,
   package staple and install Gatekeeper acceptance.
5. Ordinary updates preserve bundle ID, team ID, designated requirement, feed
   URL, Sparkle public key and trust generation.
6. Failure occurs before public download or appcast mutation.

## Output

Exit `0` only when the candidate is eligible for the public release workflow.
On failure, print a reason to stderr and leave public files unchanged. Evidence
may include identities, checksums, release IDs and status values, but never
private key material, passwords or signed URLs.
