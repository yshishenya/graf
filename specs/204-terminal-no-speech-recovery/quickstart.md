# Quickstart Acceptance: Feature 204

## Focused scenarios

1. Создать synthetic finalized meeting и импортировать result с
   `no_recognizable_speech`; проверить `manual_action=new_attempt`.
2. Вызвать admission; проверить `attempt_ordinal + 1`, новый workflow id и
   отсутствие мутации старого result/job.
3. Получить status до provider completion; проверить active state,
   `attempt_in_flight=true`, старый result не переводит projection в terminal.
4. Повторить admission во время active workflow; проверить
   `already_in_flight`/единственный active workflow.
5. Проверить quota/source/deletion/Temporal dispatch failure fences.

## Commands

```sh
pytest -q apps/server/tests/integration/test_processing_failures.py \
  apps/server/tests/contract/test_processing_status_contract.py
git diff --check
infra/scripts/ci-local.sh --fast
infra/scripts/ci-local.sh --full
```

## Production evidence

После exact-SHA deploy использовать существующую no-speech запись. Сохранять
только meeting UUID suffix, workflow/attempt ordinals, provider job count,
status codes, timestamps и health/smoke results. Не сохранять контент,
provider JSON, audio, title или credentials.

## Выполненное локальное evidence

- Feature 204 focused PostgreSQL matrix: `19 passed`.
- Expanded MediaScribe/Temporal/recovery matrix: `104 passed`.
- `git diff --check` и touched-file Ruff: pass.
- `infra/scripts/ci-local.sh --fast`: `1229 passed`, lint/compile/macOS guard pass.
- `infra/scripts/ci-local.sh --full`: macOS `766 passed`, server `3415 passed,
  1 skipped`, strict RLS `52 passed, 1 skipped`, lint/compile, compose
  validation и evidence scan pass.
- Full run был выполнен на текущем незакоммиченном worktree; после commit
  release metadata exact-SHA full gate должен быть повторён.
- RLS hardening sub-step внутри локального runner сообщил `blocked`, потому что
  production probe не выполняется против disposable PostgreSQL; это не является
  доказательством production RLS и требует отдельного production evidence.

## Production evidence

Не выполнено: нужен exact-SHA release candidate, deployment approval и
metadata-only smoke на существующей no-speech записи. До этого Feature 204 не
считается закрытой.
