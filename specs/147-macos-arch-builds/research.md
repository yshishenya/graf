# Research decisions

- One universal installer gives users one download path and lets macOS select
  the native slice. It avoids duplicate website links and architecture routing.
- Separate SwiftPM scratch paths prevent an arm64 build from being mistaken for
  an Intel build when both are produced on one host.
- The app-only package contract remains unchanged; only the executable's Mach-O
  slices and public artifact name change.
- `lipo -create` is used only after each input is verified as a single expected
  architecture.
