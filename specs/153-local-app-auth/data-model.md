# Data Model

No schema or migration changes. The only new state is an in-memory Swift
configuration boolean indicating that the explicit loopback local-app profile is
active. AuthSession, CSRF state and the `graf_dev_owner_session` cookie remain
owned by the existing server flow.
