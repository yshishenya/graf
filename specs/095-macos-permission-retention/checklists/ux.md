# UX Checklist: Permission Onboarding And Relaunch

> Historical UX checklist. It does not authorize a local/self-signed public
> release; current publication follows Feature 130.

**Purpose**: Validate requirements quality for permission onboarding,
termination, relaunch, and user-facing truth.
**Created**: 2026-07-09
**Feature**: [spec.md](../spec.md)

## User Control And Trust

- [x] Does the spec make the user the actor who grants macOS permissions?
- [x] Does the spec avoid promising that GRAF can force or preserve permissions
  after macOS sees a different app identity?
- [x] Does the spec require quiet launch when permissions are already granted?
- [x] Does the spec require specific recovery UI only when a permission is
  missing or restricted?

## Modal And Termination Behavior

- [x] Are permission onboarding sheets included in termination risk?
- [x] Are other desktop prompts, such as meeting-detection prompts, included in
  termination risk?
- [x] Is the 10-second termination reply bound measurable?
- [x] Does the spec require clearing in-progress permission request UI state so
  a spinner or stale modal cannot block quit?

## Accessibility And Copy

- [x] Does permission copy remain truthful for microphone and system-audio
  permission classes?
- [x] Does signing drift copy avoid blaming the user?
- [x] Are public-release limitations visible enough that local signing is not
  mistaken for a notarized installer?
- [x] Does the spec avoid adding new visible app text that explains internal
  implementation details to ordinary users?

## Scenario Coverage

- [x] Already-granted launch is covered.
- [x] Missing-permission launch is covered.
- [x] Permission sheet visible during quit is covered.
- [x] Normal quit with granted permissions is covered.
- [x] Signing drift that requires one-time regrant is covered.

## Notes

Checklist pass complete. Implementation should prefer small native lifecycle
and state changes over redesigning onboarding.
