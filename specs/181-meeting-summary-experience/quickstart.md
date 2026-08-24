# Quickstart: meeting summary experience

## Safety

- Use synthetic fixtures first.
- Do not print or commit transcript/output text, raw audio, credentials, signed URLs or private meeting screenshots.
- Real meetings may be evaluated only in the approved local/private pipeline; retain aggregate metadata only.
- Do not promote Langfuse prompts, deploy, release or commit implementation without the relevant explicit gate.

## Focused server validation

```sh
bash apps/server/scripts/run_local_postgres_tests.sh \
  tests/integration/test_meeting_outcomes_generation.py \
  tests/unit/test_outcome_prompts.py \
  tests/contract/test_summary_template_ui_contract.py \
  tests/integration/test_cabinet_meeting_outcomes.py -q
```

Expected:

- new revision-scoped meeting never accepts deterministic extractive output;
- automatic baseline, manual format and refresh results become current only after trusted publication;
- stale/deleted/changed-source attempts cannot replace the current slot;
- all nine formats have distinct contracts and strict source validation.

## Browser matrix

For synthetic meeting data, verify in ordinary and `/desktop` routes:

1. no accepted result: preparing, dependency unavailable, retryable and terminal states;
2. accepted result: picker, all-formats dialog, current-format refresh;
3. each of nine formats: select, pending, validated publication, automatic screen refresh;
4. duplicate click/idempotency, background/resume, reload/session recovery;
5. slow, history unavailable, preview unavailable, stale, expired, source changed, access lost and deletion active;
6. exact source seek and return;
7. keyboard only, visible focus, VoiceOver announcement sanity;
8. 1280x720, 390x844 and 200% zoom with no horizontal result overflow.

## Quality evaluation

Run each format against suitable and unsuitable synthetic cases. Record only per-format counts and rubric scores:

- faithfulness;
- attribution/owner;
- date/decision accuracy;
- actionability;
- coverage/relevance;
- type fit;
- structure/usability;
- uncertainty handling.

Any unsupported critical fact, false owner/date/final decision, missing evidence or executed transcript prompt injection is a hard fail.

## Repository gate

```sh
infra/scripts/ci-local.sh --fast
```

Full CI is reserved for the release candidate or approved deployment gate.
