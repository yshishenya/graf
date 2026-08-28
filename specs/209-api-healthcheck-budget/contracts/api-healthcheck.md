# Contract: Production API Healthcheck

- Endpoint: `http://127.0.0.1:8080/api/v1/health/ready`.
- Successful readiness must return an HTTP success status within 8 seconds.
- The internal request must fail after 8 seconds without a successful response.
- Docker must stop the healthcheck command after 10 seconds.
- The runner budget must remain greater than the internal request budget.
- Interval remains 10 seconds and retries remain 12.
- `/live` is not an acceptable replacement for this deployment gate.
