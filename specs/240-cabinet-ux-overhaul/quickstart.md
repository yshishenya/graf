# Quickstart: UX/UI/IA audit and redesign

## Preconditions

```sh
cd /Users/yshishenya/.codex/worktrees/1437/crisp/apps/server
uv sync --extra dev
```

Use the existing synthetic cabinet fixtures/harness. Never use real meeting
content, credentials, tokens or private screenshots in committed evidence.

## Focused validation

```sh
uv run --extra dev pytest -q \
  tests/contract/test_cabinet_frontend_foundation_contract.py \
  tests/contract/test_cabinet_static_assets_contract.py \
  tests/contract/test_cabinet_shell_response_contract.py \
  tests/contract/test_settings_ui_contract.py \
  tests/contract/test_billing_ui.py \
  tests/integration/test_cabinet_meeting_list.py \
  tests/integration/test_cabinet_meeting_detail.py \
  tests/integration/test_settings_ia_flow.py
node --check src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js
```

## Review matrix

For each surface in [UI surface contract](contracts/ui-surface-contract.md),
inspect 320, 390, 768, 1024 and 1440 CSS px; standalone and embedded; dark and
light; keyboard focus and reduced motion. Record only metadata and synthetic
content in `design-qa.md`.

## Closeout

```sh
cd /Users/yshishenya/.codex/worktrees/1437/crisp
infra/scripts/ci-local.sh --fast
git diff --check
```

Before opening the PR, confirm the exact 40-character `HEAD`, validate the PR
metadata, and wait for GitHub `governance-fast` on that same SHA.
