# Quickstart: meeting-list handoff

## Scope and prerequisites

Run from the repository root on branch `265-meeting-list-handoff`.

The browser scripts use the existing Playwright package under
`apps/server/tests/browser`. If it is not prepared in this worktree, run:

```sh
cd apps/server/tests/browser
npm ci
cd ../../..
```

No server, database, recording device, account, raw audio or production service
is needed for the synthetic browser scenarios below.

## Focused automated checks

```sh
node --check apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js
node --check apps/server/tests/browser/local-recording-handoff.test.cjs
NODE_PATH=apps/server/tests/browser/node_modules \
  node apps/server/tests/browser/local-recording-handoff.test.cjs
NODE_PATH=apps/server/tests/browser/node_modules \
  node apps/server/tests/browser/mixed-meeting-list.test.cjs
NODE_PATH=apps/server/tests/browser/node_modules \
  node apps/server/tests/browser/local-recording-focus.test.cjs
git diff --check
```

Expected result: each browser script prints `PASS`, there are no page errors,
and syntax/whitespace checks exit with status 0.

## Scenarios proven by the new browser check

1. A local row that changes from no `meetingId` to a new server identity starts
   one current-form refresh and remains visible before the response.
2. An authoritative response with the matching server row removes the alias and
   leaves one row.
3. Search context is serialized unchanged; selection and keyboard focus transfer
   to the server row.
4. Two handoffs in one publication share one refresh; repeated states do not
   storm the list.
5. A response that excludes the row removes the alias and does not resurrect it.
6. A failed list request keeps the local row visible and the existing retry
   completes the handoff.
7. A `401/403` response clears private server rows without deleting the native
   projection; an authorized list response later leaves one server row and no
   local duplicate.
8. A newly loaded WebView reconciles an already completed linked projection once,
   and an open delete confirmation keeps its selection and return focus when the
   local alias becomes a server row.

## Related repository checks

```sh
python3 -m pytest apps/server/tests/contract/test_cabinet_static_assets_contract.py \
  apps/server/tests/unit/test_cabinet_web_shell.py \
  apps/server/tests/unit/test_meeting_progress_ui.py
```

For the high-risk feature lane, run the focused lane after these checks:

```sh
infra/scripts/ci-local.sh --focused
```

The local lane is diagnostic evidence. Before a PR is accepted, verify
`governance-fast`, `macos-pr` and `pr-metadata` on the exact PR SHA using the
repository's current-check validator. No production deploy or release evidence
is claimed by this feature.
