# Production catalog status

Status: PENDING CONTROLLED PROVISIONING.

Read-only verification on 2026-08-21 found no personal monthly or annual rows in `billing_plan_versions`. The intended immutable rows are:

- month: 100,000 minor RUB units (1,000 RUB), unlimited processing;
- year: 1,000,000 minor RUB units (10,000 RUB), unlimited processing;
- both rows: the same storage entitlement and offer version.

No production row was inserted during implementation or testing. Provisioning is a production mutation and must run against the reviewed release with the maintenance database role during the approved release window. Readback must prove the exact two active values before the landing is called tariff-ready.
