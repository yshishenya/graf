# Contract: Secrets And Environment

## Source Policy

Production secrets for 021 use Docker secrets plus committed environment templates. Live values are provisioned outside git.

## Required Secret Classes

- Postgres application password.
- MinIO root/admin credential for MinIO initialization only.
- MinIO API access key and secret key for the Rec API.
- Internal smoke identity/device credential.
- Optional MediaScribe degraded-awareness credential reference.
- Optional Langfuse degraded-awareness credential reference.

## Required Template Rules

Committed templates MAY include:

- Variable names.
- Descriptions.
- Safe placeholder markers.
- Required/optional classification.
- Owner and rotation notes.

Committed templates MUST NOT include:

- Live values.
- Reusable local development defaults for production.
- Signed URLs.
- Credential paths that reveal secret storage internals.

## Fail-Closed Rules

Production validation MUST fail closed when:

- A required secret is missing.
- A required secret equals a known local/development default.
- API MinIO credentials appear to be root/admin credentials.
- Database or MinIO production endpoints point to localhost/wildcard addresses where inappropriate.
- Docker secret files are missing or unreadable by the intended service.

## Client Boundary

Desktop clients MUST NOT receive:

- MinIO credentials.
- MediaScribe credentials.
- Langfuse credentials.
- Direct object-storage upload URLs.
