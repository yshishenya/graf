# 119 Data Model: Expanded Meeting App Registry

**Date**: 2026-07-21

## MeetingTargetRegistryTarget

The existing schema-version-1 target shape is reused unchanged. Fork aliases are
documented in the evidence catalog and bounded `comments`; products sharing a
bundle ID remain one target and one auto-record preference.

## NativeAppIdentity

Conceptual uniqueness index over the JSON registry:

| Field | Type | Rules |
| --- | --- | --- |
| `normalized_bundle_id` | string | Lowercased stable comparison key. |
| `bundle_id` | string | Original package spelling, retained for display/evidence. |
| `target_id` | string | Exactly one owner in one registry document. |

Validation rejects duplicate normalized bundle IDs both within one target and
across targets. Resolution normalizes an observed bundle ID with the same rule.

## Evidence Catalog Item

The repository evidence catalog is the audit source and is not downloaded by
clients.

| Field | Type | Rules |
| --- | --- | --- |
| Product/family | string | User-recognizable stable family. |
| Aliases | string list | Forks/renames sharing the identity. |
| Platform | enum | macOS, browser research, excluded other platform. |
| Market | enum | global, Russia, enterprise. |
| Fingerprint | string optional | Public bundle ID or bounded service family only. |
| Evidence level | enum | Same registry evidence vocabulary. |
| Source | public reference | Package/source/vendor/distribution provenance. |
| Verified | date | Research date, not a live-call claim. |
| Runtime mode | enum | `prompt-enabled`, `blocked`, or `manual-only`; `diagnostic-only` remains schema-compatible but is unused by the 79 verified native targets in baseline 0030. |
| Notes | string | Bounded reason; no private content. |

## Registry Baseline Version

Migration 0030 owns one new global registry version and its extracted entries.

State transition on upgrade:

`published global N -> superseded global N -> published global N+1`

Workspace-scoped published/draft rows remain unchanged. On downgrade, only N+1
owned by migration 0030 is removed and the latest prior superseded global row is
restored. Target-scoped desktop preference IDs remain valid because all released
target IDs are preserved.

## Settings Read Model

The existing desktop `promptCapableTargets` read model now contains every native
target with a verified bundle ID because all are `prompt_enabled`. The existing
row and “Выбрать все” action are reused; only scrolling is added for scale.

If no cache exists, the array is empty and the settings view displays a
temporary-unavailability state; manual recording behavior is unaffected.
