# Contract: approved repair decision

The adapter accepts a decision only when all required fields from
`data-model.md` are present and non-placeholder. `affected_boundary` must be an
explicit local Dev target; values containing production hostnames, production
compose names, non-loopback origins or unknown volume ids are rejected.

Approval is a separate reviewer action. The implementation agent may prepare a
decision but must not self-approve it. A decision is immutable and can be
superseded only by a new id that names the previous decision.

The adapter MUST refuse to:

- stamp or manually edit the migration pointer;
- delete or recreate an existing volume;
- execute against production or a target whose ownership is unclear;
- continue after source SHA, backup digest or boundary changes.
