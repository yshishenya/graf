# Implementation handoff: protected dual custody

The user requested implementation of the recommended Option 2.  This handoff
turns the proposal into deliverable packages; `../tasks.md`, once generated,
is the task-level execution source of truth.

## Package 1: public trust manifest and local custody boundary

Add a versioned public manifest, make configured builds obtain/equality-check
their public key from it, and remove arbitrary local private-file use from the
operator contract.  Add a controlled Keychain/GitHub enrollment command and a
safe local verifier.  Preserve an ephemeral CI-only key-file route behind an
explicit trusted workflow context.

**Acceptance**: malformed/inactive/mismatched manifest fails; no normal local
command takes an arbitrary private file; output contains only safe key ID/status.

## Package 2: protected cloud attestation and signing

Add manual-dispatch workflows limited to the protected environment, exact tag
and least privileges.  The verifier emits a safe attestation; the signer checks
the draft asset, app, predecessor and key equality, stages signed artifacts and
uploads only to a draft release.  It cannot modify the public host.

**Acceptance**: correct secret signs a disposable draft; missing/mismatched
secret fails before signed appcast/upload; no untrusted trigger can obtain it.

## Package 3: explicit bootstrap versus ordinary update guards

Keep `validate-app-updates.sh` strict for regular appcast updates.  Add a
separate explicitly named manual bootstrap validation/package path for a trust
generation change and make staging reject that mode.  Preserve app identity,
permission descriptions and signing-lineage checks.

**Acceptance**: regular key/feed rotation fails; explicit bootstrap can be
validated but cannot produce a live appcast; post-bootstrap normal update passes.

## Package 4: evidence, operation docs and closeout

Update tests, installer README, release checklist and changelog.  Run disposable
channel tests and local CI.  After approval, enroll the real key, create the
manual bootstrap, and prove two newer in-app releases with metadata-only
evidence before declaring the new trust generation healthy.

**Acceptance**: all focused tests and canonical CI are green; no secret scan
findings; physical release remains stopped until the full manual proof is done.
