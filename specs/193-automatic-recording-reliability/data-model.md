# Data Model: Automatic Recording Reliability

No database migration is introduced. All values below are in-memory runtime state
or existing cookie/settings storage.

## Audio Ownership Event

| Field | Type | Rules |
|---|---|---|
| `bundleID` | String | Non-empty parsed native app identity |
| `source` | `audioHAL` / `sensorIndicator` | Exact producer of the transition |
| `state` | `active` / `inactive` | Source-local state only |
| `displayName` | String? | Metadata; never a meeting title |
| `processID` | Int? | Available only from AudioHAL |
| `observedAt` | Date | Ordering/debounce/end-grace input |

## Tracked Meeting Candidate

| Field | Type | Rules |
|---|---|---|
| `bundleID` | String | Candidate key |
| `activeSources` | Set<AudioOwnershipSource> | Active while non-empty |
| `firstObservedAt` | Date | Reset only at a real end or observer reconciliation |
| `latestEvent` | AudioOwnershipEvent | Display/decision metadata |
| `inactiveAt` | Date? | Set when `activeSources` becomes empty; cleared by any source start |
| `handlingState` | pending / handled / terminal | `handled` only after consumer acceptance |
| `lastRetryAt` | Date? | Enforces at least 2 seconds between retryable offers |
| `lastOutcome` | stable reason? | Deduplicates identical suppression diagnostics |

### State transitions

```text
no candidate
  -> source active -> debouncing
  -> stable + eligible -> pending trigger
  -> consumer retryable reject -> pending trigger
  -> consumer accept / Skip / manual Stop -> handled or terminal
  -> one source inactive while another active -> unchanged active
  -> all sources inactive -> end grace
  -> any source active during grace -> active
  -> grace elapsed -> ended -> no candidate
  -> observer reset -> no candidate, then snapshot rebuild
```

## Trigger Outcome

| Field | Type | Rules |
|---|---|---|
| `bundleID` | String | Existing candidate |
| `kind` | prompt / savedTarget / observed / suppressed | Existing detector decision |
| `consumerResult` | accepted / retryable(reason) / terminal(reason) | App returns after current-state check |
| `recordingReason` | prompt_button / prompt_timeout / saved_target_policy? | Preserves Feature 145 attribution |

## Observer Lifecycle

| Field | Type | Rules |
|---|---|---|
| `generation` | Integer | Monotonic within app process for diagnostics only |
| `phase` | snapshot / live / retry / stopped | Exactly one child process at a time |
| `stopRequested` | Bool | Prevents deliberate stop from restarting |
| `snapshotDeadline` | Duration | 3.5 seconds; unavailable snapshot never delays live observation indefinitely |
| `retryDelay` | Duration | Fixed 1 second; bounded below 5-second success criterion |

## Native Auth Reconciliation

The configured web origin and auth cookie name identify scope. WebKit cookies are
filtered to that origin and name. Reconciliation deletes same-scope native copies,
then inserts the current applicable web snapshot. An empty web snapshot represents
logout and leaves no same-scope native auth cookie.

Native request selection ignores empty, expired, domain/path-incompatible and
secure-on-HTTP values. Among applicable values it uses deterministic domain/path
specificity and expiry ordering. The selected value remains confined to the
existing dedicated native auth header provider and is never logged.
