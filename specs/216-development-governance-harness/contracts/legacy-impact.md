# Contract: Legacy Impact and Retirement

Every feature spec and PR includes exactly one Legacy Impact classification:

- `remove`: old runtime path is deleted and its tests/fixtures/docs are updated;
- `retain-with-exception`: compatibility is required and has owner, expiry,
  removal trigger, risk, validation and retirement task;
- `untouched`: audit found no affected legacy surface, with evidence.

The validator rejects a new alias, fallback, flag, dependency, fixture, test or
documentation path that preserves old behavior without an exception. Existing
database migrations, Temporal compatibility and client update paths require a
separate cutover feature and cannot be removed by a generic cleanup command.
