# Research: Видимый прогресс загрузки записи

## Existing flow

1. `DesktopUploadQueueItem.progressFraction` already derives a bounded ratio
   from `acceptedBytesByTrack` and the existing artifact profile. It returns `1`
   only for `uploaded` or when all accepted bytes reach the calculated total.
2. `DesktopUploadCustodySummary.showsProgress` already distinguishes an active
   upload/partial-upload projection from queued and completed summaries, but the
   compact native `localRecordingRow` does not consume that presentation signal.
3. `DesktopMeetingShellView` already owns the local rows, uses localized custody
   copy and exposes a combined accessibility label. This is the smallest surface
   that can answer the user's question without creating a second status owner.
4. `DesktopUploadQueueService` publishes queue snapshots while upload progress
   changes. No additional polling or timer is needed.

## Decisions

### Decision: show progress in the existing local recording row

**Rationale**: The launch-gap register names native upload-progress visibility as
the missing P2 state. The row is already visible for local recordings and keeps
the server WebView as the sole meeting-list authority. A new inspector or HUD
would duplicate custody truth and increase cognitive load.

**Alternatives considered**:

- A global progress HUD — rejected because it hides which local recording is
  slow and introduces a competing status surface.
- A separate upload queue screen — rejected because local upload is automatic
  custody, not a user task, and the existing contract forbids turning it into a
  transport cockpit.
- A server/WebView progress endpoint — rejected because the desktop already has
  accepted-byte truth and the feature must not add network traffic.

### Decision: use determinate progress only when total bytes are known

**Rationale**: A zero fraction can mean either an active upload at its start or
missing total metadata. The UI must not invent `0%` when no denominator exists;
it shows the existing upload copy without a percentage in that case.

### Decision: distinguish 100% bytes from `uploaded`

**Rationale**: Accepted bytes do not by themselves prove finalization, review
availability or server delivery. At 100% before the queue state changes, the
row says that sending is being checked/finalized; only `uploaded` keeps the
existing ready-to-view copy.

### Decision: no manual controls

**Rationale**: Feature 057's custody contract makes retry automatic and keeps
transport controls out of the normal user UI. Progress explains the process;
it does not turn it into a task that the user must operate.

## Validation implications

- Pure custody tests cover numeric bounds and state separation.
- A source contract protects the shared native row from losing its progress
  indicator or accidentally adding retry/stop controls.
- Swift build and canonical CI are required because the change touches the
  native capture-adjacent surface and its accessibility contract.
