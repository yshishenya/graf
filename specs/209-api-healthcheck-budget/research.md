# Research: API Healthcheck Budget

## Decision 1: Calibrate the existing healthcheck boundary

- **Decision**: Preserve `/ready` and increase only its bounded timeout pair.
- **Rationale**: Five production probes took 3.52–3.60 seconds while the internal
  request stopped at 3 seconds. Candidate health history contains matching
  `TimeoutError` entries and no startup exception.
- **Alternatives considered**: Retry unchanged deploy — rejected because every
  measured response exceeds the same cutoff. Switch to `/live` — rejected
  because it would weaken readiness. Rewrite readiness checks — rejected as a
  larger unproven change.

## Decision 2: Use 8 seconds inside 10 seconds outside

- **Decision**: Request timeout 8 seconds; Docker runner timeout 10 seconds.
- **Rationale**: The current response has more than 2x headroom, remains
  bounded, and leaves the runner two seconds to observe and terminate the
  internal command cleanly.
- **Alternatives considered**: 5/5 seconds — rejected because equal nested
  deadlines race. Unlimited wait — rejected because it defeats health gating.

## Decision 3: Pin the values in the existing contract

- **Decision**: Extend `test_production_compose_api_has_healthcheck_and_localhost_bind_policy`.
- **Rationale**: This test already owns the production API healthcheck contract;
  no new helper or test file is needed.
- **Alternatives considered**: Runtime-only smoke — rejected because it would
  not prevent a future configuration regression before deploy.
