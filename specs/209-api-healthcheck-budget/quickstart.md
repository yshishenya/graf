# Quickstart: API Healthcheck Budget

## Prerequisites

- Use the clean Feature 209 worktree.
- Do not edit the production host manually.
- Keep YooKassa in test-shop and do not create a payment.

## Focused validation

```sh
cd apps/server
uv run --extra dev pytest tests/integration/test_compose_hardening.py -q
cd ../..
docker compose --env-file infra/env/rec.production.env.example -f infra/docker-compose.yml config >/dev/null
```

Expected: healthcheck contract pins `/ready`, request timeout 8 seconds and
runner timeout 10 seconds; compose renders successfully.

## Repository and release gates

```sh
infra/scripts/ci-local.sh --fast
infra/scripts/ci-local.sh --full
infra/scripts/cd-remote.sh --dry-run --branch master
infra/scripts/cd-remote.sh --execute --branch master
```

Fast runs before PR. Full/dry-run/execute run only on the exact merged candidate.
After deploy, verify `live=200`, `ready=200`, container health and test-shop
environment metadata. Do not publish the macOS update until deploy passes.
