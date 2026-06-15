# Research: RLS Production Enforcement Truth

## Decision: Use Read-Only PostgreSQL Catalog Inspection For Production Truth

**Decision**: Verify production RLS state by reading PostgreSQL catalog
metadata for the covered tables, specifically `pg_class.relrowsecurity` and
`pg_class.relforcerowsecurity`.

**Rationale**: Production truth needs proof that RLS is enabled and forced on
live tables, but production must not receive destructive seeded cross-tenant
probe rows. Catalog inspection proves the enforcement switch state without
reading or mutating customer rows.

**Alternatives considered**:

- Run direct same/cross-tenant probes on live production: rejected because it
  seeds or mutates live customer tables and can create residue.
- Trust Alembic current only: rejected because a migration revision does not
  directly prove all covered tables have both enabled and forced RLS state.

## Decision: Keep Destructive RLS Probes On Disposable/Test Databases

**Decision**: Continue to block `RLS_TEST_DATABASE_URL` when it points at the
live `twobrain_rec` service database. Same-tenant, cross-tenant,
missing-context, worker, and maintenance probes must run only on disposable or
explicit test databases.

**Rationale**: The probe suite is valuable because it seeds two tenants and
attempts forbidden access. That is appropriate for disposable/test databases,
not live production.

**Alternatives considered**:

- Allow probes on production after backup: rejected because backup does not
  make intentional live-data mutation safe or clean.
- Remove probes after production is enabled: rejected because future changes
  still need test-gate evidence before production truth can be trusted.

## Decision: Make Validation Output Environment-Specific

**Decision**: Replace blanket `live_production_enforcement=not_changed`
language with output that distinguishes:

- test/disposable validation that does not touch live production;
- production read-only verification that proves live enforcement state;
- blocked states that name missing or failed evidence.

**Rationale**: The current wording is technically safe but now misleading. It
was correct for destructive probe safety, but it reads like production RLS is
not enabled even when production table metadata proves enabled and forced.

**Alternatives considered**:

- Leave wording as historical `031` behavior: rejected because future product
  slices need truthful current production security status.
- Say only `enabled`: rejected because it loses the important distinction
  between test probe results and production table-state inspection.

## Decision: Keep Covered Table Inventory Traceable To The 031 Migration

**Decision**: Production table-state verification must use the same covered
table set as `0005_rls_hardening.py`, either by sharing the inventory or by a
contract test that prevents drift.

**Rationale**: A production truth check is only useful if it covers the same
tables as the actual RLS migration. Separate handwritten lists can drift.

**Alternatives considered**:

- Query every public table and require RLS: rejected because non-tenant support
  tables such as Alembic metadata may not be tenant-owned.
- Maintain a separate docs-only list: rejected because it can silently diverge
  from migration policy coverage.

## Decision: Correct Status Docs As Part Of This Feature

**Decision**: Update `docs/current-product-status.md`,
`docs/deployments/2brain-rec/rls-hardening-runbook.md`,
`docs/adr/003-tenant-isolation-rls.md`, `CHANGELOG.md`, and relevant `031`
evidence notes to describe the current production truth.

**Rationale**: This is a truth and evidence correction, not only a code helper.
Leaving stale docs would keep the product roadmap in a false state.

**Alternatives considered**:

- Only add a new verifier: rejected because status consumers would still read
  old "not changed" claims.
- Rewrite all `031` history: rejected because historical task artifacts should
  remain traceable. Correction notes should distinguish past pre-production
  wording from current verified production state.
