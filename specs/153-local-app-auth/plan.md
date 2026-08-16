# Implementation Plan: Авторизация в локальном macOS-приложении

Risk/validation lane: high-risk-feature. Reuse the existing Swift cabinet state,
route policy and WebKit session. Add one local-only configuration flag and make
auth recovery target the existing login route when a local request has no usable
session. Production defaults remain unchanged because the branch is gated by an
explicit flag plus an HTTP loopback origin.

Validation: focused Swift cabinet tests, local bundle rebuild/launch, shell
syntax, and `infra/scripts/ci-local.sh --fast`.

Constitution check: PASS. No capture path, public signing path, production auth
cookie, legacy header, secret, OAuth provider or deployment behavior changes.
