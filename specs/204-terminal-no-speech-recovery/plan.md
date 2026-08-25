# Implementation Plan: Повторная обработка no-speech

**Risk lane**: `high-risk-feature` — MediaScribe, Temporal, Postgres,
idempotency и user-facing recovery.

## Approach

1. В `processing/store.py` определить подтверждённый no-speech result по
   текущей revision и `processing_workflow_id`, и допустить его как terminal
   admission case.
2. В `processing/status.py` применять no-speech override только когда result
   относится к текущему workflow; active newer workflow имеет приоритет.
3. Добавить минимальные integration/API regression tests на admission,
   projection после создания и повторный клик.
4. Запустить focused checks, fast lane, полный exact-SHA CI и затем, после
   отдельного approval, deployment/smoke по release guidance.

Production defect follow-up: новые попытки и manual same-job check должны
получать Temporal client через общий ленивый, кешируемый API helper. Наличие
client в `app.state` не является обязательным условием для первого recovery
запроса после старта или перезапуска API.

## Invariants

- Не менять MediaScribe client, Temporal workflow contract или provider retry
  semantics без failing test.
- Сохранить quota reservation, deletion epoch, source fingerprint и tenant
  fences.
- Не менять пользовательские тексты для иных terminal причин.
- Evidence остаётся metadata-only.

## Validation

- Focused processing failure/status/API suites.
- `git diff --check` и `infra/scripts/ci-local.sh --fast`.
- Перед release: `infra/scripts/ci-local.sh --full` на exact SHA.
- После approval: `cd-remote.sh --dry-run`, затем controlled production deploy и
  metadata-only smoke на существующей no-speech записи.
