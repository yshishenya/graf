# Security and privacy requirements checklist

- [x] The no-account Gatekeeper limitation is explicit; no requirement promises
  public trust without Developer ID/notarization.
- [x] The supported user path does not disable Gatekeeper globally or ask for
  unsafe terminal workarounds.
- [x] The installer verifies the app and nested code before packaging.
- [x] Release validation fails closed when the app signature lacks the
  hardened-runtime Audio Input entitlement.
- [x] Microphone and Screen/System Audio states are read from macOS and are not
  manufactured by application state.
- [x] The feature does not reset/edit TCC, install PPPC profiles, or add a
  privileged audio component.
- [x] Validation evidence excludes audio, transcript text, credentials, raw TCC
  databases, and private meeting content.
