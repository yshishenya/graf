# Data Model: Code Optimization

## Cleanup Candidate

- `id`: stable local identifier for the candidate
- `path`: file path containing the candidate
- `symbol_or_block`: function, class, helper, import, branch, script, or block
- `category`: `delete now`, `shrink now`, `keep intentionally`, or
  `risky / needs spec`
- `evidence`: caller/import/runtime searches and inspected entrypoints
- `risk_surface`: auth, deletion, capture, processing, desktop, infra, or none
- `validation`: focused checks required before marking complete
- `runtime_loc_delta`: expected line impact excluding docs/spec files
- `dependency_delta`: dependency impact, usually zero

## Cleanup Batch

- `scope`: one narrow runtime surface
- `candidates`: one or more cleanup candidates with evidence
- `accepted_changes`: candidates actually removed or shrunk
- `kept_intentionally`: inspected candidates retained with reason
- `deferred_risky`: candidates requiring separate spec or broader validation
- `validation_evidence`: commands and outcomes
- `net_runtime_loc_delta`: final runtime line impact

## Evidence Record

- `search_commands`: commands used to prove callers/imports
- `runtime_entrypoints`: routes, scripts, Docker, SwiftPM targets, templates, or
  tests checked
- `limits`: what the evidence does not prove
- `follow_up`: next action when evidence is incomplete
