# Data Model: Feature 228 legacy retirement process

Feature 228 хранит только metadata. Реестр не содержит пользовательский текст,
сырой контент или production rows и не заменяет `tasks.md`.

## LegacyContour

| Поле | Тип | Ограничение |
|---|---|---|
| `contour_id` | string | immutable, stable, safe identifier |
| `category` | enum | alias, fallback, flag, dependency, fixture, docs, migration, temporal, media, macos, deploy |
| `source_path` | string | repository-relative, contained path |
| `source_digest` | `sha256:<64 hex>` | digest of the cited source artifact |
| `source_sha` | 40-hex SHA | exact inspected commit |
| `status` | enum | `candidate`, `approved`, `blocked`, `retired` |
| `classification` | enum/null | `remove`, `retain-with-exception`, `untouched`; absent while a `candidate`/`blocked` contour is awaiting classification |
| `owner` | string | required for approved/blocked decisions |
| `risk` | enum/string | rationale is required |
| `rationale` | string | metadata-only explanation |
| `evidence` | list | relative paths/issue/PR references only |
| `linked_feature` | string | `F###` when a slice exists |
| `linked_issue` | integer | GitHub issue number |
| `linked_task` | string | canonical `T###` task owning the next action |

## LegacyException

`retain-with-exception` records additionally require `compatibility_boundary`,
`reason`, `owner`, future ISO `expiry`, `removal_trigger`, `validation` and
`retirement_task`. Missing or expired fields fail closed.

## RetirementSlice

Each removal slice records `feature_id`, `contour_ids`, `scope_fence`, owner,
`risk_lane`, supported client/data boundary, `protected_domain`, Dev rehearsal,
abort conditions, rollback target, exact validation commands,
`known_limitations`, and links to the GitHub issue, PR, task and release
evidence. The same rollback and independent validation must cover every contour
in a grouped slice.

## Evidence lifecycle

`candidate → approved → retired` is reviewer/owner controlled. A candidate or
blocked record has no classification until that decision is recorded. A blocked record
may return to `candidate` after remediation, but `blocked → retired` is never
valid. Source SHA or registry digest changes invalidate prior evidence as
`stale`; stale metadata cannot authorize merge, release or deletion.
