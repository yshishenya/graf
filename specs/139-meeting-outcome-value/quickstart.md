# Quickstart: meeting-outcome-value

Все fixtures должны быть synthetic. Не печатать transcript/output/judge feedback,
tokens, credentials, signed URLs или live secret paths.

## Focused implementation loop

```sh
cd apps/server
python -m pytest -q \
  tests/unit/test_outcome_prompts.py \
  tests/unit/test_summary_candidate_revisions.py \
  tests/unit/test_prompt_optimization.py \
  tests/unit/test_prompt_optimization_validation_retry.py \
  tests/unit/test_cabinet_view_models.py \
  tests/unit/test_cabinet_web_shell.py \
  tests/contract/test_summary_template_ui_contract.py \
  tests/integration/test_meeting_outcomes_generation.py \
  tests/integration/test_recording_share_public_link.py \
  tests/integration/test_transcript_export_egress.py
```

Для database-backed тестов использовать изолированный runner:

```sh
apps/server/scripts/run_local_postgres_tests.sh --focused -q <exact files above>
```

Затем:

```sh
ruff check apps/server/src apps/server/tests
node --check apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js
git diff --check
```

## Required scenarios

1. First usable transcript → accepted fast baseline + ровно один queued Auto
   candidate/dispatch intent; replay/reload не создаёт второй provider identity.
2. AI disabled/default invalid/no speech/deleted/stale → transcript/baseline
   остаются, candidate имеет truthful bounded state.
3. Empty/duplicate/wrong-sequence ref, non-action owner/due и invalid state parity
   rejected до candidate readiness.
4. Confirmed speaker name передаётся стабильно; один участник с несколькими
   сегментами не превращается в `Speaker 1…N`; unknown остаётся unknown.
5. Candidate preview показывает русскую IA, owner/due и source before accept;
   accept/reject не меняют прошлую версию разрушительно.
6. Accepted AI item имеет seekable timestamp из server-side enrichment.
7. Owner/full-viewer/summary-only/share/export получают только разрешённый
   accepted projection; summary-only browser entry не возвращает JSON.
8. Processing/blocked/no-summary/no-player используют aggregate state и не
   создают fake source action.
9. Keyboard source action переключает tab, seek и focus; timeline работает по
   Enter/Space; heading outline остаётся последовательным.
10. Desktop и 390 CSS px не имеют horizontal overflow.

## Prompt/eval gate

```sh
python -m twobrain_rec_server.cli.langfuse_prompts --help
```

Сначала dry-run exact desired hashes. Изменённые prompts публикуются только как
unlabelled candidates. Production promotion допускается после:

- versioned synthetic development + private held-out manifests;
- 0 critical unsupported/attribution/injection failures;
- action precision ≥98%, recall ≥90%; owner/due precision и unknown restraint
  100%; must-unit recall 100%, weighted coverage ≥90%;
- beginning/middle/end long-context pass без hidden truncation;
- human judge calibration и operator approval;
- rollback target и protected sole mutation credential readiness.

Committed receipt содержит hashes/versions/counts/metrics/error codes, но не
content или free-form feedback.

## Browser evidence

Через выбранный in-app Browser снять текущий-run before/after для owner accepted,
candidate, processing, no-player и summary-only на desktop и 390 CSS px. Проверка
скриншота дополняется runtime interaction/focus assertions; screenshot сам по
себе не считается QA.

## Repository and release gates

Перед PR:

```sh
infra/scripts/ci-local.sh --fast
```

Implementation commit предлагается только после focused + fast evidence и
явного user approval. Перед release/deploy:

```sh
infra/scripts/ci-local.sh --full
infra/scripts/cd-remote.sh --dry-run --branch master
```

`--execute`, merge, tag/GitHub Release и public Developer ID package выполняются
только после соответствующих gates и approvals по
`docs/agent-guidance/release-and-validation.md`.
