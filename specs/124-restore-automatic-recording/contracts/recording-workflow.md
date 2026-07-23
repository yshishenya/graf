# Contract: Native Automatic Recording Workflow

This is a user-facing and policy-facing contract for the macOS meeting
detection flow. It is intentionally implementation-light; source paths are
listed only for traceability in the plan/tasks.

## Settings Contract

The Meeting Detection settings page MUST expose:

1. The `detect-and-ask` toggle named «Запрашивать запись».
2. One «Приложения» section explaining that checked applications are written
   automatically and other verified applications ask first.
3. Every verified macOS native prompt-capable target from the canonical registry.
4. A reversible checkbox/toggle for every target.
5. «Выбрать все» and «Снять все» actions.
6. Persistence through the existing target-scoped settings document and change
   notification.

No browser, unknown, diagnostic-only, future-platform or unverified target may
appear as an auto-record row.

## Prompt Contract

For a stable known target without a saved target-scoped auto-record permission,
the floating prompt MUST:

- remain visible above normal app surfaces;
- show the detected app and capture source/policy explanation;
- show the Russian opt-in checkbox «Всегда писать это приложение»;
- show a visible eight-second progress countdown;
- start immediately when the user invokes the primary action;
- start automatically when eight seconds expire and all gates still pass;
- provide a dismiss action («Пропустить» in the restored legacy copy);
- cancel all timer work on Start, dismiss, disappearance or resolved state.

The prompt cannot start if the same capture session is active or if a
prerequisite is unavailable. A disabled prompt must explain that recording is
currently unavailable rather than silently starting later.

Repeated detector outputs must be coalesced while a prompt or detector-assisted
start is active. The scheduling interval before the shared capture path marks
`recordingStartInProgress` is covered by a transient trigger guard; it must not
create a second prompt or recording task.

## Policy Contract

```text
known target + detectAndAsk + prerequisites pass + target ID enabled
    => autoRecord(targetID)

known target + detectAndAsk + prerequisites pass + target ID not enabled
    => prompt(targetID)

any unknown/suppressed/non-prompt/blocked/active-session condition
    => detectOnly or suppress; never autoRecord
```

The target ID is the canonical identity used by the registry and settings. A
bundle ID or display name may describe the evidence but cannot broaden a saved
permission to another target.

## Capture Contract

Both the timer expiry and the auto-record policy action MUST enter the existing
detector-assisted capture start path. That path MUST continue to enforce:

- microphone and system-audio permission gates;
- workspace policy and source eligibility;
- storage/readiness and recording-prerequisite gates;
- persistent local visible recording state;
- one-action Stop;
- one active capture session per device;
- existing local custody/upload/deletion behavior.

The contract does not include the removed separate audio-routing implementation,
any new audio engine, arbitrary system audio, bot joining or calendar start.

## Regression-Protection Contract

The source and tests MUST keep positive checks for the settings list,
`autoRecord`, `autoRecordEligible`, `countdownSeconds`, `autoStartTask`, the
checkbox, and the restored labels. A future cleanup that removes any of these
must be treated as a contract change and routed through a new approved Spec Kit
feature with migration/compatibility notes.
