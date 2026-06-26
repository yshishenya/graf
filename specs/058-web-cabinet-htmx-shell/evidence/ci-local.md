# Local CI Evidence: 058 Web Cabinet HTMX Shell

Date: 2026-06-26

## Result

`ci_local_result=pass`

## Command

```sh
infra/scripts/ci-local.sh
```

## Observed Output

- Server tests: `691 passed, 4 skipped, 94 warnings`
- Server lint: `All checks passed`
- Python compile: passed
- RLS hardening validation boundary: `rls_validation_result=blocked` because the destructive/test database proof environment was not provided; this remains a bounded validation boundary, not a feature failure.
- Production compose config: rendered successfully with secret placeholders.
- Deployment evidence scan: `pass`
- Final result: `ci_local_result=pass`

## Evidence Hygiene

The raw CI output included local machine paths and placeholder locations, so
this committed evidence records only metadata-safe result counts and bounded
status labels. It does not include raw audio, transcript text, generated
outcome text, object keys, signed URLs, credentials, private local paths, or
real account identifiers.
