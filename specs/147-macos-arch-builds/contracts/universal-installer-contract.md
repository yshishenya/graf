# Universal installer contract

1. `build-local-installer.sh` defaults to `apps/macos/.build/installer/graf.pkg`.
2. The distribution has one component: `graf-desktop-app.pkg`.
3. The staged executable reports exactly `arm64` and `x86_64` via `lipo -archs`.
4. `pkgutil --payload-files` contains no `.driver`, HAL plug-in, or driver
   package reference.
5. `/download` has exactly one `downloads/graf.pkg` link and no architecture
   choice.
6. Public release requires the existing Developer ID and notarization gates.
