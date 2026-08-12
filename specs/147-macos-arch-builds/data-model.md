# Data Model: Universal macOS Installer

This feature does not add database tables or persistent application data. The
release artifact model is a metadata contract used by the build and validation
surfaces.

## Release artifact

| Field | Meaning | Constraint |
|---|---|---|
| `product_version` | CalVer release version | Same in bundle, package, and release notes |
| `bundle_identifier` | macOS application identity | `pro.2brain.graf` |
| `minimum_macos` | Lowest supported OS | `14.5` unless separately changed |
| `architectures` | Native executable slices | Exactly `arm64` and `x86_64` |
| `installer_filename` | Public package filename | Stable `graf.pkg` |
| `signing_state` | Local/release signing result | Release must use approved Developer ID signing |
| `notarization_state` | Apple notarization result | Required before public release |
| `driver_components` | Legacy routing component presence | Must be absent |
| `validation_evidence` | Metadata-only checks | Must not contain secrets or private content |

## Invariants

- One release version maps to one public installer URL.
- The installer contains one GRAF bundle with both native slices.
- The two slices share product identity and behavior.
- A failed architecture or packaging check blocks publication.
