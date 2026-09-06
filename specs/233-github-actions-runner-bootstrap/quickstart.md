# Quickstart: Feature 233

```sh
python3 scripts/validate-governance-workflow.py .github/workflows/governance-fast.yml
python3 scripts/check_spec_kit_governance.py
python3 scripts/check-development-process.py
```

После публикации workflow открыть PR и убедиться, что check `governance-fast`
прошёл на exact SHA. Локальный fallback запускать только для диагностики:

```sh
infra/scripts/ci-local.sh --fast
```
