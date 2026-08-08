# Research: Safe macOS App Updates

## Decision 1: Use Sparkle 2.9.4 and pin the exact stable release

**Decision**: Add the official Sparkle Swift Package at exact version `2.9.4`, released 2026-07-03.

**Rationale**: Sparkle is the established self-hosted macOS update framework and already owns the difficult parts this feature must not reimplement: scheduling, appcast parsing, release UI, authenticated archive validation, privileged replacement when needed, rollback, and relaunch. Version 2.9.4 is the current stable release and includes the signed-feed and hardware-requirement capabilities used by this design.

**Alternatives considered**:

- A custom downloader/replacer: rejected because it duplicates security-critical update, rollback, authorization, and relaunch logic.
- Mac App Store updates: rejected because GRAF is currently self-hosted and distributed through its own installer/download surface.
- A shell-only “download latest package” action: rejected because it cannot provide safe scheduling, coherent UI state, atomic app replacement, or trustworthy rollback.

**Sources**: [Sparkle 2 documentation](https://sparkle-project.org/documentation/), [Sparkle 2.9.4 release](https://github.com/sparkle-project/Sparkle/releases/tag/2.9.4)

## Decision 2: Keep `.pkg` for bootstrap; update the regular app bundle from a signed archive

**Decision**: The existing app-only `.pkg` remains the first/manual install path. Sparkle updates use a versioned archive containing `GRAF.app`.

**Rationale**: GRAF is a regular app bundle with no privileged audio component. A normal bundle update gives Sparkle its strongest atomic replacement and rollback path and usually avoids the authorization ceremony required for package updates. The archive keeps the same app path, bundle ID, and signed application identity.

**Alternatives considered**:

- Use the existing `.pkg` for every update: supported by Sparkle but rejected for the default path because package updates always require installer authorization and have a less direct bundle rollback model.
- Add a privileged updater daemon: rejected; Sparkle already handles authorization when the installation location requires it.

**Sources**: [Sparkle publishing guide](https://sparkle-project.org/documentation/publishing/), [Sparkle package updates](https://sparkle-project.org/documentation/package-updates/)

## Decision 3: Preserve TCC permissions through stable designated requirement

**Decision**: Every release keeps `GRAF.app`, `pro.2brain.graf`, `/Applications/GRAF.app`, the same signing lineage/team, and a compatible designated requirement. Release validation compares old and new code-signing identity before publication.

**Rationale**: macOS uses a code object’s designated requirement to decide whether an updated app is the same code that was previously granted microphone access. Changing certificate lineage or designated requirement can cause permission prompts even when the visible app name and bundle ID stay unchanged.

**Alternatives considered**:

- Depend on bundle ID alone: rejected because bundle ID is not the complete macOS code identity.
- Reset or edit TCC during update: prohibited and unnecessary; validation must observe the real permission state without mutating it.

**Source**: [Apple TN3127: Inside Code Signing — Requirements](https://developer.apple.com/documentation/technotes/tn3127-inside-code-signing-requirements)

## Decision 4: Use Sparkle standard UI plus gentle scheduled reminders

**Decision**: `SPUStandardUpdaterController` owns manual checks and update dialogs. Scheduled updates use `SPUStandardUserDriverDelegate` gentle reminders: show the standard dialog when capture is idle, but suppress an interrupting scheduled dialog and show the left-sidebar marker while protected capture work is active.

**Rationale**: The standard UI is accessible and handles all update stages. Gentle reminders are the official mechanism for a custom in-app availability marker without replacing Sparkle’s installer UI. Manual checks always bring Sparkle’s standard UI into focus.

**Alternatives considered**:

- Fully custom updater UI: rejected because it would duplicate stage, authorization, error, and release-note handling.
- Always show scheduled dialogs: rejected because an update alert may interrupt a recording workflow.
- Badge only, never an automatic offer: rejected because the user explicitly asked to be offered an available update.

**Sources**: [Programmatic setup](https://sparkle-project.org/documentation/programmatic-setup/), [Gentle update reminders](https://sparkle-project.org/documentation/gentle-reminders/)

## Decision 5: Postpone relaunch and installation while capture work is protected

**Decision**: The updater controller keeps one current protected-work flag and uses Sparkle’s relaunch-postponement callback. If installation reaches the relaunch boundary during capture, transitions, finalization, or termination cleanup, the install continuation is retained and invoked only after the protected work becomes idle.

**Rationale**: This is the shared root boundary for menu, scheduled, sidebar, and already-downloaded updates. One gate is smaller and safer than separate guards in every UI action.

**Alternatives considered**:

- Disable only the sidebar/menu during capture: rejected because an already-open Sparkle window or downloaded update could still request relaunch.
- Cancel the update when capture starts: rejected because the user should not have to download/check again after recording.

**Source**: [SPUUpdaterDelegate reference](https://sparkle-project.org/documentation/api-reference/Protocols/SPUUpdaterDelegate.html)

## Decision 6: Sign the archive, feed, and release notes; verify before extraction

**Decision**: Release builds set `SUPublicEDKey`, `SUVerifyUpdateBeforeExtraction=YES`, and `SURequireSignedFeed=YES`. Update archives, appcast, and release notes are generated/signed by Sparkle tools. The EdDSA private key stays in an operator keychain or approved secret store, separate from the public host and repository.

**Rationale**: HTTPS protects transport, while EdDSA protects authenticity even if the host is compromised. Signed feeds prevent an attacker from presenting a malicious location or release description. Verification before extraction reduces exposure to untrusted archive contents.

**Alternatives considered**:

- HTTPS only: rejected because compromise of the hosting origin would still control update metadata.
- Commit the private key or run signing on the public host: prohibited by repository secret policy and weakens supply-chain separation.
- Allow an unsigned fallback: rejected; incomplete trust configuration disables updates instead.

**Sources**: [Sparkle customization and security settings](https://sparkle-project.org/documentation/customization/), [Sparkle publishing guide](https://sparkle-project.org/documentation/publishing/)

## Decision 7: Use the existing public GRAF download host, not private GitHub Releases

**Decision**: Default feed URL: `https://rec.2brain.pro/static/public/downloads/graf-appcast.xml`. Each enclosure uses a versioned archive name such as `GRAF-2026.07.17.1.zip` under the same HTTPS download surface.

**Rationale**: The repository is private, so unauthenticated clients cannot depend on GitHub Release assets. GRAF already operates a public HTTPS download surface for the installer. Reusing it avoids a new storage service and embedded credentials.

**Alternatives considered**:

- Private GitHub Releases: rejected because the desktop app would need credentials.
- A new object-storage/CDN subsystem: deferred until update volume or reliability measurements justify it.
- One mutable archive filename: rejected because an in-flight download could race with publication of a later version.

## Decision 8: Let Sparkle own the 24-hour schedule and user defaults

**Decision**: Configure `SUEnableAutomaticChecks=YES`, `SUScheduledCheckInterval=86400`, `SUAutomaticallyUpdate=NO`, `SUAllowsAutomaticUpdates=NO`, and `SUEnableSystemProfiling=NO` in release Info.plist. Do not add a second timer or preference store.

**Rationale**: Sparkle already enforces the schedule, launch catch-up, minimum interval, and persisted user state. A parallel timer risks duplicate checks and inconsistent state. The requested behavior is “offer,” not silent background installation.

**Alternatives considered**:

- A custom periodic `Task.sleep` loop: rejected because it duplicates Sparkle scheduling and can interfere with its update cycle.
- Automatic download/install: rejected because it conflicts with explicit user choice and capture safety.
- System profiling: disabled because it is unnecessary for this feature and expands the data sent with checks.

**Sources**: [Sparkle customization](https://sparkle-project.org/documentation/customization/), [System profiling](https://sparkle-project.org/documentation/system-profiling/)

## Decision 9: Fail closed when update configuration is incomplete

**Decision**: The app starts Sparkle only when the main bundle contains a valid HTTPS feed URL and public EdDSA key. Ad-hoc/local builds without those values show an unavailable manual-check result and no badge.

**Rationale**: Sparkle deliberately reports configuration errors, but release-incomplete local builds are normal in this repository. A small preflight prevents insecure fallbacks and avoids misleading automatic alerts.

**Alternatives considered**:

- Ship placeholder keys or URLs: rejected because a placeholder can accidentally reach production.
- Fall back to opening the download web page: rejected because it bypasses the signed update and permission-retention contract.

## Decision 10: Defer channels, mandatory updates, phased rollout, and delta retention

**Decision**: Initial scope is one stable full-archive channel. Sparkle’s additional capabilities are not configured yet.

**Rationale**: They are not required to satisfy the user request and add release-policy, storage, and support complexity. The chosen appcast format keeps them available later.

**Alternatives considered**:

- Add beta/stable channels now: rejected without a beta audience or release policy.
- Force critical/mandatory updates: rejected because capture availability and user control are non-negotiable.
- Retain delta history immediately: deferred until archive size and update volume make the operational cost worthwhile.
