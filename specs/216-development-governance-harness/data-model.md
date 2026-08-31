# Data Model: Governance and Dev Harness

## FeatureClaim

| Field | Rule |
|---|---|
| `feature_id` | Three-digit immutable Spec Kit ID; unique across visible specs, branches, issues and PRs |
| `umbrella_issue` | GitHub issue URL/number used as reservation record |
| `slug` | Canonical feature directory/branch slug |
| `owner` | GitHub login or explicit local owner |
| `status` | `reserved`, `active`, `closed`, `retired` |
| `created_at` | UTC timestamp |
| `source_sha` | Integration base used when claim was created |

Transitions: `reserved → active → closed → retired`. A duplicate or abandoned
claim is never silently reused; it is marked with a replacement/link.

## AgentContextManifest

Contains only bounded routing data: `feature_id`, `umbrella_issue`, `branch`,
`feature_directory`, `active_task`, `risk_lane`, `release_gate`, `source_sha`,
`owned_paths` and links to the constitution/guidance files. It MUST NOT contain
secrets, raw audio, transcript text or full historical logs.

## ChangelogFragment

`schema_version`, `feature_id`, `category` (`Added`, `Changed`, `Fixed`,
`Security`, `Docs`, `Ops`), Russian `summary`, optional `compatibility`,
`known_limitations`, `issue`, `tasks`, and `created_at`. The file name is
namespaced by Feature ID and may be written only by its feature owner.

## DevManifest

`schema_version`, `manifest_id`, `parent_manifest_id`, `feature_id`, `source_sha`,
`backend_digest`, `frontend_digest`, `worker_digests`, `migration_head`,
`app_bundle_id`, `app_designated_requirement`, `app_code_signature_digest`,
`operator`, `promoted_at`, `health_status`, `smoke_status`, `rollback_target`.

The active pointer is atomic. A manifest with mismatched component SHAs,
unknown migration head or failed smoke cannot become active.

## CIRunEvidence

`run_id`, `lane`, `requested_sha`, `observed_sha_start`, `observed_sha_end`,
`status` (`passed`, `failed`, `stale`, `cancelled`, `ambiguous`), `started_at`,
`finished_at`, `commands`, `artifact_digests`, `skipped_gates`, `reason`.

## ReleaseCandidate

`candidate_id`, frozen `source_sha`, included Feature IDs, changelog snapshot
digest, full-run ID, one go/no-go decision, CalVer, tag/release URLs, rollback
target and known limitations. Any source or metadata change invalidates the
candidate and requires a new candidate ID.

## LegacyException

`surface`, `reason`, `owner`, `expiry`, `removal_trigger`, `retirement_task`,
`risk`, `validation` and `status`. Exceptions are not valid without all fields;
expired or ownerless records block merge/release.

## HarnessRelease

Immutable SemVer, source commit, project adapter contract, supported tool
versions, self-test result, secret/path scan result, migration notes and
rollback version.
