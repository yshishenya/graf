# Research: Cabinet Web Split

## Decision: Split Route Families, Not Domain Behavior

**Decision**: 073 splits only the cabinet web route layer. It does not change
templates, view models, egress/download/export behavior, deletion service,
auth provider behavior, database models, migrations, infra, or deploy scripts.

**Rationale**: 072 identified `cabinet/web.py` as a reviewability problem, not a
broken product behavior. The safest product-improving move is to reduce the
monolithic route file while preserving every route contract.

**Alternatives considered**:

- Rewrite cabinet rendering or move to a new frontend pattern: rejected as
  too broad and not required by the first roadmap batch.
- Split view models/egress in the same PR: rejected because 072 put those in
  later batches and they carry separate export/deletion risk.

## Decision: Keep Public Router Import Stable

**Decision**: `twobrain_rec_server.cabinet.web.router` remains the public router
import used by `apps/server/src/twobrain_rec_server/main.py`.

**Rationale**: Keeping the import path stable minimizes app wiring risk and
lets the split be reviewed as internal cabinet organization.

**Alternatives considered**:

- Change `main.py` to include many cabinet routers: rejected because that
  leaks cabinet internals into app composition and increases route ordering
  risk.

## Decision: Prefer Existing Tests Over New Scaffolding

**Decision**: Use the existing cabinet contract/integration/unit tests as the
primary regression proof. Add a minimal test only if the move reveals a route
family contract that is not covered.

**Rationale**: Ponytail: the smallest useful proof is the tests already guarding
cabinet behavior. New test scaffolding is only useful when it catches a real
uncovered moved boundary.

**Alternatives considered**:

- Add snapshot tests for every route: rejected as noisy and brittle for a
  behavior-preserving split.
- Run production smoke: rejected because 073 is not a deploy slice.

## Decision: Shared Helpers Need One Owner

**Decision**: Helpers used across route families should either stay in the
public web assembly module or move to a small shared support module. They must
not be copied into multiple route modules.

**Rationale**: Duplication would make future auth/CSRF/deletion changes riskier
than the current monolith.

**Alternatives considered**:

- Duplicate small helpers inside each route family: rejected because login,
  calendar, deletion, and desktop routes share security-sensitive behavior.

## Decision: Stop If Behavior Coupling Is Larger Than Expected

**Decision**: If moving a route requires changing auth/deletion/calendar/egress
semantics, stop and record the finding instead of widening the PR.

**Rationale**: The user explicitly asked for actions that improve the product,
not a prettier diff that weakens behavior.

**Alternatives considered**:

- Force the full split in one PR: rejected because it would violate the 072
  small-batch roadmap.
