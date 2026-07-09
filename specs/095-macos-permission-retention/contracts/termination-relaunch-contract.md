# Contract: Termination And Relaunch With Permission Modals

## Purpose

Define how GRAF must behave when macOS, the installer, or the user asks the app
to quit while permission onboarding or another desktop modal is visible.

## Scope

In scope:

- permission onboarding sheet;
- in-progress permission request UI state;
- meeting-detection prompt state;
- AppKit attached sheets;
- `applicationShouldTerminate` cleanup and reply behavior;
- installed-app quit/relaunch validation.

Out of scope:

- forced process kill;
- active-recording discard behavior outside existing capture safety rules;
- changing macOS System Settings behavior;
- hidden permission grants or resets.

## Required Termination Flow

When `NSApplicationDelegate.applicationShouldTerminate` is called:

1. If a termination reply is already pending, return `.terminateLater`.
2. Record metadata-only `app_termination_cleanup_requested`.
3. Dismiss attached AppKit sheets and clear SwiftUI modal state that can block
   termination.
4. Notify app content to run normal cleanup.
5. Reply `true` when cleanup completes.
6. If cleanup does not complete within the existing 10-second bound, reply
   `true` with a timeout reason.

The modal dismissal step must run before user-facing sheets can block the
reply.

## Runtime State To Clear

The termination path must clear or dismiss:

- `permissionOnboardingPresented`;
- `permissionOnboardingRequestInProgress`;
- meeting-detection prompt state;
- attached AppKit sheets on visible windows;
- detached sheet windows when a sheet parent exists.

The path must not:

- start recording;
- open System Settings;
- request new permissions during termination;
- silently reset permission decisions;
- hide active recording state while capture is active.

## Acceptance Scenarios

### Permission Sheet Visible

Given the permission onboarding sheet is visible, when quit is requested, then
the sheet is dismissed, cleanup is requested, and macOS receives a termination
reply within 10 seconds.

### Permissions Already Granted

Given microphone and Screen/System Audio are granted, when the app appears or
quits, then permission onboarding is not presented.

### Meeting Detection Prompt Visible

Given a meeting-detection prompt is visible, when quit is requested, then the
prompt state is cleared and cannot block the termination reply.

### Reentrant Termination Request

Given a termination reply is pending, when macOS asks again, then the app
returns `.terminateLater` and does not schedule duplicate cleanup replies.

## Evidence Events

Allowed log/event labels:

```text
app_termination_cleanup_requested
app_termination_cleanup_completed
desktop.permission_onboarding_checked
```

Allowed reason values:

```text
cleanup_finished
timeout
app_appeared
permission_recheck
```

Evidence must record only metadata such as event name, reason, permission state
labels, and elapsed time. Do not record window screenshots with private content.

## Validation Methods

Use both:

- focused Swift tests or source-level assertions for the presence of modal
  dismissal and state clearing; and
- installed-app manual/AppleScript validation to prove the real app quits.

Suggested installed-app quit check:

```sh
osascript -e 'tell application "GRAF" to quit'
```

Expected:

- `GRAF` process exits;
- latest log includes cleanup completion or timeout reason;
- no permission sheet remains blocking macOS.
