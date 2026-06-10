# Production Environment Templates

This directory contains safe committed environment templates for 2brain Rec
deployment.

Templates may include variable names, placeholder markers, owners, rotation
expectations, and failure behavior. They must not include live secret values,
signed URLs, credential paths that expose private storage internals, or local
development defaults intended for production.

For local-file Docker Compose secrets, the host secret files must be readable by
the non-root runtime group inside the server image. On `2brain.dev`, the runtime
group maps to numeric GID `101`; keep secret files owner-readable for the
operator and group-readable for that runtime group, for example `0640`.
