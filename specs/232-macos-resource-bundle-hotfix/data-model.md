# Data Model: Безопасный запуск macOS после обновления

No persistent product-data model or migration is introduced.

## Release candidate metadata

- `source_sha`: exact 40-character commit used for build and validation.
- `version`: CalVer strictly newer than `2026.09.02.1`.
- `app_path`: extracted candidate `GRAF.app` used by startup smoke.
- `binary_architectures`: expected `arm64` and `x86_64` slices.
- `resource_bundle_path`: standard `Contents/Resources` bundle location.
- `startup_duration_seconds`: minimum five seconds.
- `artifact_sha256` and `artifact_bytes`: derived from final stapled ZIP/PKG.
- `publication_state`: draft assets -> versioned download files -> live appcast.

These fields are metadata-only release evidence. They are not stored in the
application database and contain no user or meeting content.

## State transitions

```text
built -> signed -> notarized -> stapled -> validated -> uploaded -> appcast-live
```

Every transition is fail-closed. Changing source SHA or artifact bytes creates
a new candidate; it never mutates earlier evidence.
