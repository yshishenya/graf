# Production preview receipt — 2026-07-21

## Release and deploy

- Release: [`v2026.07.21.13`](https://github.com/yshishenya/crisp/releases/tag/v2026.07.21.13)
- Release PR: [#4086](https://github.com/yshishenya/crisp/pull/4086)
- Deployed and runtime SHA: `0b923f7e4c1198c39ba17951bd0ced7f2d7bcc3f`
- `deploy_result=pass`, protected backup and restore rehearsal passed.
- Runtime database identity, strict RLS validation, metadata-only production
  smoke, automatic dispatch, cleanup, public `/health/live`, and public
  `/health/ready` passed.

## Controlled owner-preview policy

The initial production read-back found `65` existing meetings and `0` accepted
per-meeting artifact-policy rows. This is the intended fail-closed default from
Feature 017, so the deployed export control correctly remained disabled until
an explicit policy was accepted.

For the current owner-preview corpus, a bounded `workspace_default` seed added
one policy snapshot to each of the `65` existing meetings:

- transcript export: `owner_only`;
- summary export: `owner_only`;
- audio download: `disabled`;
- legacy package export: `disabled`.

The seed does not grant team or shared viewers export access, does not enable
audio egress, does not enable public links, and does not weaken per-request
access, revision, deletion, audit, or readiness checks.

## Installed-app read-back

- The already installed `/Applications/GRAF.app` opened the production cabinet;
  no native application rebuild or reinstall was required because Feature 120
  is a server/WebView slice.
- Before the accepted seed, the owner meeting showed a disabled export entry
  point with a policy reason.
- After navigation refreshed the server read model, the same ready owner
  meeting exposed the enabled top-level export entry point and server-mediated
  transcript egress.
- A meeting without a stored summary continued to report summary as missing;
  the UI did not regenerate or fabricate one.
- No transcript text, summary text, raw audio, meeting title, private identifier,
  object key, signed URL, or exported file is stored in this receipt.

## Remaining gates

- T059 / [issue #4083](https://github.com/yshishenya/crisp/issues/4083)
  remains open. This deployment is a controlled owner preview, not the
  representative-reviewer study or a general-release acceptance claim.
- The accepted seed covers the current production corpus. A newly created
  meeting still resolves to the conservative disabled default until an explicit
  accepted policy snapshot is created; automated workspace-policy provisioning
  remains separate product work.
- An already downloaded copy remains outside later GRAF revocation and deletion.
