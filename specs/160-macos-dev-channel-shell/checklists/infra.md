# Infrastructure and Release Checklist: macOS Dev Channel and Native Home

- [x] The disposable local build and public installer remain separate entrypoints.
- [x] The Dev command verifies signer, bundle ID, origin, storage namespace, and no-feed metadata.
- [x] Installation is atomic and does not replace `/Applications/GRAF.app`.
- [x] Public notarization/Sparkle/appcast gates remain owned by the release guidance and are not weakened.
- [x] Same-identity rebuild/update and production+Dev coexistence are in the validation matrix.
