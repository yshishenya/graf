# Plan

1. Add a PostgreSQL RLS contract proving the two context boundaries.
2. Flush trusted browser session/device writes under request context.
3. Reapply the existing exact auth-bootstrap context before callback completion
   and audit commit.
4. Run targeted browser-auth and PostgreSQL RLS tests, then the canonical CI
   gate before the hotfix PR and release lane.
