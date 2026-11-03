# Contract: Legacy Impact and Retirement

Every feature spec and PR includes exactly one Legacy Impact classification:

- `remove`: old runtime path is deleted and its tests/fixtures/docs are updated;
- `retain-with-exception`: compatibility is required and has owner, expiry,
  removal trigger, risk, validation and retirement task;
- `untouched`: audit found no affected legacy surface, with evidence.

The text validator checks the declaration and the required fields of a bounded
exception; it does not discover changed paths or prove consumer migration.
Review must separately inspect affected consumers and reject any new alias,
fallback, flag, dependency, fixture, test or documentation path preserving old
behavior without a valid exception. Existing
database migrations, Temporal compatibility and client update paths require a
separate cutover feature and cannot be removed by a generic cleanup command.
