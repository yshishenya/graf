# Quickstart: Meeting Outcomes MVP

This guide validates 049 before PR, release, and production closeout. Evidence
must remain metadata-only.

## Prerequisites

```sh
SPECIFY_FEATURE_DIRECTORY=specs/049-meeting-outcomes-mvp \
  bash .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
```

Expected outcome:

- feature directory resolves to `specs/049-meeting-outcomes-mvp`;
- `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`,
  `quickstart.md`, and `tasks.md` are present.

## Focused Server Validation

Run focused tests from the server package:

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/contract/test_meeting_outcomes_contract.py \
  tests/integration/test_meeting_outcomes_generation.py \
  tests/integration/test_cabinet_meeting_outcomes.py \
  tests/integration/test_meeting_outcomes_deletion.py \
  tests/unit/test_meeting_outcomes_generator.py \
  tests/unit/test_meeting_outcomes_view_models.py \
  tests/unit/test_cabinet_web_shell.py \
  tests/contract/test_cabinet_no_secret_content_egress.py
```

Expected outcome:

- stored outcomes are generated for transcript-ready owner meetings;
- categories support available/not-found/not-inferable/processing/blocked
  states;
- factual items include transcript segment or timestamp evidence;
- denied/deleted/deleting/unavailable states expose no outcome content;
- transcript/playback remain visible when outcomes are processing or blocked;
- metadata-only assertions pass.

## Migration And RLS Validation

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/integration/test_processing_migrations.py \
  tests/integration/test_meeting_outcomes_migrations.py \
  tests/contract/test_rls_tenant_isolation_contract.py
```

Expected outcome:

- new tables exist in the model/migration contract;
- new tables are included in RLS coverage constants;
- no RLS table coverage regression is introduced.

## Browser Runtime Validation

```sh
NODE_PATH="<bundled-node-modules>" "<bundled-node>" \
  specs/049-meeting-outcomes-mvp/evidence/browser-runtime-check.cjs
```

Expected outcome:

- ordinary web review, mobile-width web review, and desktop embedded review
  render matching outcome category states;
- available categories show stored outcome content and evidence;
- processing/blocked/partial states remain truthful;
- transcript and bottom playback controls remain usable;
- no horizontal overflow or incoherent overlap is reported;
- evidence output contains only metadata such as counts, state names, timings,
  and boolean checks.

## One-Hour Outcome Orchestration Budget

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/integration/test_meeting_outcomes_orchestration_benchmark.py
```

Expected outcome:

- one-hour synthetic transcript generation with local/fake dependencies finishes
  within 30 seconds, or records a safe non-blocking processing/blocked state
  without delaying transcript/playback review.

## Readiness Truth Validation

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/integration/test_mvp_loop_readiness_report.py \
  tests/unit/test_mvp_loop_readiness_matrix.py
```

Expected outcome:

- readiness closes `notes-action-output` only when stored outcomes are proven;
- otherwise readiness keeps the blocker open or records an explicit
  owner-approved deferral.

## Forbidden Content Scan

Scan feature docs/evidence before closeout:

```sh
find specs/049-meeting-outcomes-mvp -type f ! -name quickstart.md -print0 \
  | xargs -0 rg -n '(/Users/|/private/|/var/folders|BEGIN (RSA|OPENSSH|PRIVATE) KEY|sk-(proj|live|test|svcacct)-[A-Za-z0-9_-]+|Bearer [A-Za-z0-9._-]+|https?://[^ ]*X-Amz-Signature|signed_url=|signedUrl=|storage_object_key|transcript_text|transcriptText|outcome_text|outcomeText|prompt_text|promptText|model_response|raw_audio|rawAudio)' || true
```

Expected outcome:

- no matches.

## Full Local CI

```sh
infra/scripts/ci-local.sh
```

Expected outcome:

- `ci_local_result=pass`;
- server tests, lint, compile, RLS boundary, compose config, and deployment
  evidence scan complete without feature regressions.

## Deploy Dry-Run

```sh
infra/scripts/cd-remote.sh --dry-run
```

Expected outcome:

- `deploy_result=dry_run`;
- planned remote path, branch sync, backup, restore rehearsal, secret scan,
  build/up, smoke, and public health steps are listed.

## Closeout Evidence Rules

Do not commit:

- raw audio;
- transcript text;
- generated outcome text;
- prompts with meeting content;
- model/provider responses with meeting content;
- private meeting names or IDs;
- screenshots containing private meeting content;
- credentials, tokens, signed URLs, storage object keys, or private paths.

Record only metadata: state names, category counts, item counts, timings,
validation command names, pass/fail results, and safe reason codes.
