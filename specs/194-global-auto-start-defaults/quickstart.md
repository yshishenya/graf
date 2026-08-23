# Quickstart: Global policy and first-run prompt

## Server

1. Run config tests for disabled, scoped and approved global policy.
2. Render Compose and confirm the new variables are passed only to `rec-api`.
3. In the contract fixture, enable global scope and request the registry using
   two authenticated tenant scopes; assert `scope=all_workspaces`, opaque refs,
   and no raw IDs.

## Desktop

1. Use a temporary settings URL with no file and a synthetic registry containing
   native prompt-capable, browser and diagnostic targets.
2. Resolve the registry and assert `detectAndAsk`, target-scoped auto-record and
   only native prompt-capable IDs; assert the marker is persisted.
3. Edit the settings to remove a target, resolve a later registry, and assert the
   edit remains unchanged.
4. With active policy but no acknowledgement, feed a stable native event and
   assert a prompt output; invoke prompt button and assert current manual start
   is allowed without persisted ack; invoke timeout/saved-target and assert
   assisted start remains blocked.
5. Select «Всегда писать это приложение», persist the exact acknowledgement and
   assert subsequent timeout/saved-target decisions pass only while policy,
   workspace, device, permissions, storage, indicator and Stop remain current.

## Evidence limits

Use synthetic IDs and metadata-only assertions. Do not record a real meeting or
persist audio, transcript, cookie, token or credential values in evidence.
