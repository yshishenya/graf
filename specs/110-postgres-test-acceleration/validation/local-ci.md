# Validation: canonical local CI

## Result

`infra/scripts/ci-local.sh` completed with `ci_local_result=pass` after the
test-pipeline implementation and again after the final compatibility-fixture
cleanup.

The canonical gate verified:

- macOS legacy-audio guard, Swift build, 571 Swift tests and native contract
  validation;
- the complete 1,827-node server PostgreSQL gate, including its strict serial
  RLS phase and disposable-container cleanup;
- Ruff, Python compilation, production Compose rendering and deployment-evidence
  scanning.

The RLS hardening command correctly reports a non-production probe as blocked
when no explicitly supplied live database exists. This is expected local safety
behaviour, not a claim of a production probe. PostgreSQL RLS behaviour itself
is exercised by the strict serial test phase above.

No deploy, release, production database access or real user data operation was
performed for this feature.
