# Release checklist

- [X] One `graf.pkg` artifact and one public link.
- [X] `arm64` and `x86_64` source binaries built separately.
- [X] Final app binary verified universal with `lipo`.
- [X] Installer contains one desktop component and no driver component.
- [X] macOS 14.5 minimum is enforced.
- [X] Developer ID package signing, notarization and staple completed for
      production (`v2026.08.12.3`).
- [X] Live public download receipt after deploy: `/download` and
      `downloads/graf.pkg` returned HTTP 200 on 2026-08-13; public SHA-256
      matched the notarized release asset.
