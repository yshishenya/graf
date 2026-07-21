# Registry Expansion Contract

Feature 119 preserves schema version 1 and the existing target shape in
`specs/092-automatic-meeting-detection/contracts/meeting-target-registry.schema.json`.

## Native Identity Invariant

For every `nativeBundleIds` value in the document:

```text
lowercase(bundleID) -> exactly one target.id
```

Server publication and desktop cache acceptance reject violations. Desktop
resolution uses the same lowercase key. Forks with the same bundle ID use one
target; their names remain evidence-catalog/comments metadata.

## Prompt Mode Invariant

A `prompt_enabled` native target requires:

- at least one verified macOS bundle ID;
- identity evidence other than `verify_required` or `future_windows`;
- explicit user target selection before auto-record;
- the existing workspace policy, capture prerequisites, visible recording
  indicator, and one-action Stop.

Runtime evidence is post-enable QA and upgrades the evidence label to
`runtime_verified`; it is not required to place a verified native app in the
common prompt/auto-record list.

## Compatibility

No schema version or client model field changes. The ETag continues to cover the
complete canonical document; older clients receive more existing-shape targets.
