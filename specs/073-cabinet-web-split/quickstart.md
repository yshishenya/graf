# Quickstart: Validate Cabinet Web Split

Run from repository root:

```sh
git status --short --branch
.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
```

Expected:

- Branch is `codex/073-cabinet-web-split`.
- Active feature directory is `specs/073-cabinet-web-split`.
- Product behavior changes are not part of the diff.

## Focused Regression Gates

```sh
uv --project apps/server run --extra dev pytest -q \
  apps/server/tests/contract/test_cabinet_contract.py \
  apps/server/tests/contract/test_cabinet_csrf_contract.py \
  apps/server/tests/contract/test_cabinet_no_secret_content_egress.py \
  apps/server/tests/integration/test_cabinet_csrf.py \
  apps/server/tests/integration/test_cabinet_hx_fragments.py \
  apps/server/tests/integration/test_cabinet_meeting_detail.py \
  apps/server/tests/integration/test_cabinet_meeting_list.py \
  apps/server/tests/integration/test_cabinet_web_access_states.py \
  apps/server/tests/integration/test_meeting_deletion_workflow.py \
  apps/server/tests/integration/test_web_owner_session_context.py \
  apps/server/tests/unit/test_cabinet_web_shell.py
```

If calendar route code moves:

```sh
uv --project apps/server run --extra dev pytest -q \
  apps/server/tests/contract/test_calendar_no_secret_content_egress.py \
  apps/server/tests/integration/test_calendar_deletion_lifecycle.py
```

Always run:

```sh
git diff --check
```

## Stop Conditions

Stop and split into a separate Spec Kit slice if implementation requires:

- changing auth/session/provider behavior;
- changing deletion or retention semantics;
- changing egress/download/export behavior;
- changing desktop WebView route policy;
- changing database models or migrations;
- changing dependencies, infra, or deploy scripts.
