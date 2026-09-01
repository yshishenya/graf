# Contract: Metadata-only legacy registry

The canonical machine-readable shape is `governance/legacy/registry.schema.json`
planned by T008. This contract defines the invariants that schema validation
alone cannot express.

1. Every record has a stable `contour_id`, contained repository-relative
   `source_path`, source digest and exact source SHA.
2. Discovery emits only `candidate` or `blocked`; a match never authorizes
   deletion.
3. Records are sorted by `contour_id`; identical source SHA and inputs produce
   identical ordering and registry digest.
4. Content-bearing fields are forbidden, including credentials, signed URLs,
   raw audio, transcript text, private meeting content and database rows.
5. `retain-with-exception` is valid only with a future expiry, owner, bounded
   compatibility boundary, removal trigger, validation and linked task/issue.
6. A changed source SHA or registry digest marks prior evidence stale.

The registry points to task/issue ownership; it does not copy task descriptions
or the full issue history into always-on agent context.
