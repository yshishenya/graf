# 119 Research: Expanded Meeting App Registry

**Date**: 2026-07-21

## Decisions

### Package Identity Is Recognition Evidence, Not Recording Evidence

**Decision**: Accept a current signed package, official source definition, or
maintained detector/distribution manifest as sufficient identity evidence for a
`prompt_enabled` macOS target. Keep auto-record behind explicit user selection
and the existing prerequisite, visible-state, policy, and Stop gates. Record
target-specific AudioHAL/false-positive results as post-enable QA.

**Rationale**: The user explicitly chose breadth-first rollout and accepts that a
wrong fingerprint may fail to trigger. Existing explicit target selection and
capture gates still prevent silent default auto-record.

**Alternatives considered**: Silently selecting every package-verified app for
existing users would violate the explicit recording-choice gate. Omitting the
apps from the selectable list would leave known activity indistinguishable from
unknown candidate discovery.

### Bundle IDs Are Case-Insensitive And Globally Unique Within The Registry

**Decision**: Normalize bundle identifiers with Unicode-independent lowercase
for matching and duplicate validation on both server and macOS. Reject a whole
remote registry if one case-folded identity is claimed by two targets.

**Rationale**: Apple documents `CFBundleIdentifier` as the bundle's unique
identifier and bundle identifier comparisons as case-insensitive. Matching and
validation must use the same rule so a case variant cannot bypass ownership.

**Source**: Apple `CFBundleIdentifier` documentation and Bundle Programming
Guide; package `Info.plist` inspection remains the preferred concrete source.

### Telegram Families Use Runtime Identity, With Shared-ID Forks As Aliases

**Decision**:

- Telegram for macOS / former Telegram Lite: `ru.keepcoder.Telegram`.
- Telegram Desktop: `com.tdesktop.Telegram`.
- TDX, Forkgram, and 64Gram: aliases of Telegram Desktop because their current
  macOS packages/source use `com.tdesktop.Telegram`.
- Telegram A: `org.telegram.TelegramA`.
- AyuGram Desktop: `one.ayugram.AyuGramDesktop`.
- Kotatogram Desktop: `io.github.kotatogram`.

All verified native identities start prompt-enabled in the common applications
list. Their live matrix is post-enable QA. Bettergram and other
abandoned, mobile-only, Windows-only, Linux-only, or identity-unverified forks
are listed as deferred rather than represented as current macOS runtime targets.

**Evidence**: Current official Telegram package `Info.plist`; Telegram Desktop,
AyuGram, 64Gram, and Kotatogram build definitions; Forkgram package
`Info.plist`; maintained distribution metadata for Telegram A. Local installed
Telegram Desktop and AyuGram identities corroborated the source values. A
metadata-only log check did not establish a complete live call start/end receipt.

### Expand Native Coverage Before Browser Claims

**Decision**: Add verified native identities broadly. Preserve the implemented
browser resolver families—Telemost, Google Meet, Zoom, Teams, and Pruffme—and
record the broader provider research as pending until a production adapter can
construct safe joined-page evidence.

**Rationale**: The current app can consume synthetic `BrowserTargetEvidence`,
but no production component constructs it. Calendar links can classify a
service family, not prove a joined page. Generic browser audio remains suppressed.

**Research sources**: MeetingBar's maintained provider catalog; official vendor
pages and maintained package manifests for Zoom, Teams, Webex, Jitsi, Chime,
RingCentral, GoTo, Whereby, Around, Livestorm, 8x8, Vonage, and regional VKS.

### Publish A New Immutable Global Baseline

**Decision**: Add migration 0030 with a new registry document. Upgrade
supersedes only currently published global versions; workspace-specific rows
remain untouched. Downgrade deletes only the migration-owned version and
restores the newest prior global version.

**Rationale**: Editing migration 0019 data cannot update deployed databases and
would make historical migrations non-reproducible.

### Show Recognition Status Without Multiplying Controls

**Decision**: Reuse the existing one scrollable applications list and checkbox
row for every verified native target. “Выбрать все” explicitly opts into the
complete set; no new UI mode or read model is needed.

**Rationale**: The expanded registry should be visible without implying that
recognition equals safe automatic recording. One runtime identity produces one
row even when several products share it.

## Evidence Quality Ladder

1. `runtime_verified`: current live start/end plus safety matrix.
2. `installed_verified`: local package identity inspected; prompt-capable.
3. `package_verified`: current package or official build manifest; prompt-capable.
4. `confirmed` / `seed`: maintained detector/distribution metadata; prompt-capable.
5. `verify_required`: product known but no safe current macOS identity; blocked or manual-only.

## Rejected Scope

- No Windows process detector, mobile app identity, or Linux desktop claim.
- No bundle scanning or installed-app inventory collection.
- No raw unified-log evidence, meeting URL, room code, title, attendee, audio,
  or transcript committed as research evidence.
- No new browser extension, Accessibility permission, or calendar-data store.
- No guessed fingerprint based only on product name or popularity.

## Remaining Release Evidence

Every newly catalogued product still needs an actual account/call where feasible,
idle/prejoin/join/end receipt, voice-message and media false-positive checks,
resource observation, and recording-control validation as post-enable QA. The
catalog enables identity-based prompt and user-selected auto-record behavior,
but does not claim successful live-call verification for pending entries.
