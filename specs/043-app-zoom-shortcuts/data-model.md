# Data Model: App Zoom Shortcuts

## WorkspaceZoomPreference

Represents the local desktop user's selected meeting workspace scale.

Fields:

- `value`: numeric zoom factor.
- `defaultValue`: `1.0`.
- `minimumValue`: `0.8`.
- `maximumValue`: `1.4`.
- `step`: `0.1`.

Validation rules:

- Values below the minimum normalize to the minimum.
- Values above the maximum normalize to the maximum.
- Missing, non-finite, or invalid persisted values normalize to the default.
- Increase and decrease commands move by one step and then clamp.
- Reset command returns to the default.

Lifecycle:

1. App starts and loads the saved preference.
2. Invalid or absent values fall back to default.
3. User triggers a zoom command.
4. The preference updates in memory and persists locally.
5. Embedded workspace receives the current value on creation and update.

## WorkspaceZoomCommand

Represents one user-triggered zoom action.

Values:

- `increase`: one step up.
- `decrease`: one step down.
- `reset`: default value.

Validation rules:

- Command-Plus and Command-Equals map to `increase`.
- Command-Minus maps to `decrease`.
- Command-0 maps to `reset`.

## NativeShellBoundary

Represents the invariant that native capture/upload/readiness controls remain
outside workspace zoom.

Fields:

- `captureRegionScaled`: must be `false`.
- `stopReachable`: must be `true` when active recording can stop.
- `uploadTruthScaled`: must be `false`.
- `localAudioReadinessScaled`: must be `false`.
- `workspaceZoomApplied`: current workspace zoom value.

Validation rules:

- Applying workspace zoom must not change native shell control scale.
- Applying workspace zoom must not change route, upload, recording, or deletion
  state.
