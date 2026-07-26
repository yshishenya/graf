# Data model: release trust states

The feature does not add a database table. These filesystem/release entities are
the state model used by scripts and operator evidence.

## Public release candidate

Fields:

- `releaseRef`: CalVer tag such as `v2026.07.26.6`.
- `commit`: exact reviewed Git commit.
- `app`: `GRAF.app` signed by `Developer ID Application`.
- `package`: optional public `.pkg` signed by `Developer ID Installer`.
- `notarization`: Apple acceptance and staple evidence for each published
  artifact.
- `gatekeeper`: `spctl` acceptance evidence.
- `checksums`: SHA-256 for versioned public assets.
- `releaseNotes`: Russian notes without secrets or meeting content.

Validation rules:

- app/package identities, hardened runtime, notarization, stapling and
  Gatekeeper are required before public mutation;
- tag, commit and version must agree;
- versioned assets are immutable and must not be silently overwritten.

## Migration bootstrap

Fields:

- `predecessor`: historical local/self-signed or ad-hoc app identity;
- `candidate`: Developer ID app with the same bundle identity and compatible
  product metadata;
- `package`: notarized Developer ID installer package;
- `feed`: same feed URL and Sparkle public key as the predecessor when present;
- `publication`: `manual-pkg-only`, with `appcast_staged=no`.

State transition:

```text
legacy client -> manual notarized Developer ID .pkg -> Developer ID client
```

The transition is not an in-app Sparkle update and must never be represented by
an ordinary appcast item.

## Ordinary Sparkle update

Fields:

- `previous`: Developer ID app already trusted by the channel;
- `candidate`: newer Developer ID app;
- `bundleIdentifier`, `teamIdentifier`, `designatedRequirement`;
- `feedURL`, `sparklePublicKey`, `trustGeneration`.

Validation rules: all lineage fields remain compatible; the signing kind must
remain Developer ID; archive and appcast validation may run only after those
checks pass.

## Historical receipt

An immutable release/deployment/checklist/spec record with an explicit
`historical`/`archive` label. It can describe a prior local/self-signed
artifact but cannot be used as a current build instruction or public release
gate.
