# Meeting Mute Truth Fixtures

Fixture files are intentionally metadata-only.

Rows:

- `pause-validated.json`: product Pause is validated, meeting-app mute remains unproven.
- `unsupported.json`: unknown target fails closed as unsupported.
- `deferred.json`: Yandex Browser + Telemost is deferred until adapter evidence exists.
- `unsafe.json`: intentionally includes forbidden content and must be detected as blocked.
