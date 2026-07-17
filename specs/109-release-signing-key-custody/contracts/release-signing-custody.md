# Contract: custody подписи обновлений

This is an operator and automation contract.  It intentionally contains no
private key, secret value, password, signed URL or machine-specific path.

## Public Manifest Contract

`apps/macos/Installer/UpdateSigningKey.json` is the only version-controlled
source of active Sparkle public trust.  A configured production build must read
its public key from the active manifest or receive an explicitly equal value;
it must reject an unset, malformed or unequal value.

```json
{
  "schemaVersion": 1,
  "status": "active",
  "trustGeneration": 2,
  "keyId": "sha256:<64 lowercase hexadecimal characters>",
  "publicKey": "<base64-encoded 32-byte Ed25519 public key>",
  "channels": {
    "primary": {
      "kind": "github-environment",
      "environment": "graf-release-signing",
      "secretName": "GRAF_SPARKLE_ED25519_PRIVATE_KEY"
    },
    "recovery": {
      "kind": "macos-keychain",
      "account": "graf-release-signing"
    }
  }
}
```

The example names are identifiers, not secrets.  The actual key values are
intentionally omitted from this contract.

## Local Provisioning Contract

`provision-release-signing-custody.sh` is a controlled owner command.

| Input | Required behavior |
| --- | --- |
| `--initialize` | Explicitly requests creation of a new signing generation; routine runs cannot replace an existing active account. |
| `--keychain-account` | Non-secret Keychain account name; must match manifest after activation. |
| `--github-environment` | Protected environment name; secret transfer is stdin/temporary-file only and removed on exit. |
| `--verify` | Runs local public-key derivation and asks the protected workflow for a safe attestation. |

Outputs contain only `keyId`, trust generation, channel state, and next action.
The command fails if a generated/imported key does not match the public manifest
being activated.  It must not print, commit, attach, or preserve private bytes.

## Readiness Verification Contract

`verify-release-signing-custody.sh` accepts a candidate `GRAF.app`, the public
manifest and a GitHub safe attestation artifact.  It validates:

1. manifest schema, status, public-key length and `keyId`;
2. equality of manifest key and candidate `SUPublicEDKey`;
3. equality of Keychain-derived public key and manifest;
4. equality of protected-workflow attested `keyId` and manifest;
5. freshness/identity of the requested tag when the check is release-bound.

Output is line-oriented safe metadata, for example:

```text
key_id=sha256:…
keychain=ready
github_environment=ready
overall=ready
```

No path, secret name value, command invocation containing a secret, account
contents or raw key material may appear.  `overall=degraded` is informative;
only an explicitly approved fallback release can proceed with one channel.
`overall=unavailable` always blocks staging/publication.

## Protected Workflow Contract

Two manually dispatched workflows live on the protected default branch.

| Workflow | Environment | Inputs | Allowed output | Forbidden behavior |
| --- | --- | --- | --- | --- |
| `verify-release-signing-custody.yml` | `graf-release-signing` | expected public `keyId`, immutable tag | safe attestation artifact/summary | pull-request trigger, secret output, public feed modification |
| `sign-graf-app-update.yml` | `graf-release-signing` | version, tag, prior version | validated signed ZIP, appcast, SHA-256, safe attestation to draft release | public-host publish, untrusted ref, arbitrary local key file, automatic live rollout |

Both use least `contents: read` permissions except the signing job's scoped
draft-release upload permission.  They must only check out/operate on the exact
approved tag after confirming it is the intended `master` release commit.  The
Sparkle secret is materialized only in a restrictive runner-temporary file,
deleted by an exit trap, and never included in an artifact/output/cache.

## Ordinary Staging Contract

`prepare-app-update.sh` has two mutually exclusive signer modes:

- `keychain`: local recovery signer, permitted only through the manifest's
  named account;
- `ephemeral-ci`: protected workflow temporary key file, permitted only when
  the trusted workflow context and restrictive file permissions are present.

It no longer accepts a general-purpose local private-file environment variable.
For either mode it derives the signer's public key and requires equality with
the active manifest and the candidate app before creating a ZIP or appcast.
It retains the existing atomic staging replacement and never uploads/publishes.

## Bootstrap And Release Contract

The manual bootstrap validation command is named explicitly and may allow one
key-generation transition only while building a manual package.  It cannot be
used by `prepare-app-update.sh`, and the normal validator keeps rejecting a
changed feed/public key.

After bootstrap, a normal release must satisfy this sequence:

```text
candidate app + previous app + approved tag
  -> protected signer key equality check
  -> signed draft ZIP/appcast + checksum
  -> owner verifies draft assets
  -> versioned files copied to host and re-fetched
  -> public appcast replaced last
  -> in-app update proof
```

The first protected-signer update and one more sequential update are both
required release evidence.  A failed preflight, signer mismatch, unavailable
channel, missing archive, or invalid appcast leaves the current public appcast
unchanged.
