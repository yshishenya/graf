# Contract: manual Developer ID migration bootstrap

## Invocation

```sh
apps/macos/Installer/Scripts/validate-developer-id-bootstrap.sh \
  /path/to/new/GRAF.app \
  /path/to/previous/GRAF.app \
  /path/to/notarized/GRAF-version.pkg
```

## Required behavior

- The new app is `Developer ID Application`, has the expected GRAF bundle
  identity, hardened runtime, valid staple and Gatekeeper acceptance.
- The package is signed by `Developer ID Installer`, has a valid notarization
  staple and passes `spctl --assess --type install`.
- The previous app is accepted only as a historical predecessor for this
  explicitly named mode; its local/self-signed kind is never accepted by the
  ordinary public update mode.
- Existing feed URL and Sparkle public key, when present, remain unchanged.
- `GRAF_UPDATE_ARCHIVE` and `GRAF_UPDATE_APPCAST` are empty; the wrapper emits
  `publication=manual-pkg-only` and `appcast_staged=no`.

## Forbidden behavior

- Do not call this validator as an ordinary Sparkle update.
- Do not pass an archive or appcast.
- Do not change the live appcast for the legacy→Developer ID transition.
- Do not accept local, self-signed, ad-hoc or owner-only identities as the new
  public candidate.
