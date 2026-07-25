# Data Model: Видимый прогресс загрузки записи

## No persisted model change

Feature 128 adds no stored entity, database field, queue schema version or
server contract. The UI consumes the existing `DesktopUploadQueueItem` snapshot
and `DesktopUploadCustodyProjection`.

## Presentation values

| Value | Source | Rule |
|---|---|---|
| `uploading` | `DesktopUploadQueueItem.state` | The only local state that can show active progress. |
| `progressFraction` | Existing item projection | Bounded to 0…1; derived from accepted bytes and existing total bytes. |
| `progressPercent` | Rounded display value | 0…100, shown only when the total denominator is positive. |
| `finalizing` copy | Existing uploading row + `progressPercent == 100` | Says verification/finalization is continuing; never says ready. |
| `uploaded` | Existing item state | Existing ready-to-view text; no active progress bar. |
| `accessibilityLabel` | Existing combined row label | Includes the same state and percentage that the visible row communicates. |

## State transitions

```text
queued/retrying/local-only --(existing custody runner)--> uploading
uploading + accepted bytes --> uploading + updated progressFraction
uploading + all accepted bytes --> uploading + finalizing copy
uploading --(existing server finalization)--> uploaded
```

The UI does not create, persist, or infer any transition. It only presents the
current snapshot. A stale or missing snapshot keeps the existing bounded state.

## Privacy and safety boundary

Progress is metadata-only. It must never include meeting title, local path,
recording bytes, transcript, storage URL, server identifier, token or secret.
