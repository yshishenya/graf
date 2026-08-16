# Quickstart Validation

## Focused server checks

From the repository root:

```sh
cd apps/server
pytest -q tests/unit/test_cabinet_view_models.py -k 'title or meeting_list_row'
```

Expected: calendar, app-context, generic, authoritative, unsafe, Unicode,
long-title, missing-time, and HTML-safe title cases pass.

Run the focused cabinet integration slice with the repository's local Postgres
runner:

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused \
  tests/integration/test_cabinet_meeting_detail.py
```

Expected: the browser and embedded desktop meeting list/detail paths expose the
same projected title and existing access/deletion behavior remains unchanged.

## macOS compatibility checks

```sh
swift test --package-path apps/macos --filter RecordingMetadataResolver
swift test --package-path apps/macos --filter DesktopUploadClient
```

Expected: the client continues sending existing title/source/time metadata and
stable local media basenames remain unchanged.

## Closeout

```sh
infra/scripts/ci-local.sh
```

No deployment, release, signing, or audio-file rename command is part of this
feature.
