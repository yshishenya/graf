# Contract: Global Assisted Auto-Start Policy

## Environment

```text
TWOBRAIN_ASSISTED_AUTO_START_ENABLED=false
TWOBRAIN_ASSISTED_AUTO_START_ALL_WORKSPACES=false
TWOBRAIN_ASSISTED_AUTO_START_ALL_WORKSPACES_APPROVED=false
TWOBRAIN_ASSISTED_AUTO_START_WORKSPACE_ID=
TWOBRAIN_ASSISTED_AUTO_START_POLICY_VERSION=
TWOBRAIN_ASSISTED_AUTO_START_ACKNOWLEDGEMENT_VERSION=
TWOBRAIN_ASSISTED_AUTO_START_POLICY_ISSUED_AT=
TWOBRAIN_ASSISTED_AUTO_START_POLICY_EXPIRES_AT=
```

When `ALL_WORKSPACES=true`, `ALL_WORKSPACES_APPROVED=true` is mandatory and the
workspace ID must be empty. When the global flag is false, the existing exact
workspace ID is mandatory.

## Registry response

```json
{
  "assistedAutoStartPolicy": {
    "scope": "all_workspaces",
    "policyRef": "sha256:<64 hex chars>",
    "acknowledgementSubjectRef": "sha256:<64 hex chars>",
    "deviceRef": "sha256:<64 hex chars>",
    "policyVersion": "2026.08.23.1",
    "acknowledgementVersion": "2026.08.23.1",
    "enabled": true,
    "issuedAt": "2026-08-23T00:00:00Z",
    "expiresAt": "2026-09-22T00:00:00Z",
    "noticeMode": "internal_no_participant_notice"
  }
}
```

`scope=workspace` is returned for the existing configured-workspace mode.
Omitting `assistedAutoStartPolicy` remains the fail-closed response.

## Desktop behavior

- A clean settings directory enables detection and all verified native targets
  after the first valid registry.
- A target without current acknowledgement still produces the regular prompt.
- Prompt button is explicit current-user start and does not synthesize ack.
- Prompt timeout and saved-target automatic start require the exact current ack.
- Selecting «Всегда писать это приложение» and confirming the prompt persists the
  existing policy/subject/device-bound acknowledgement.
