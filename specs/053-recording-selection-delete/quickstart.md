# Quickstart: Recording Selection And Delete

## Focused Checks

Run the server tests that cover the list shell and deletion lifecycle:

```sh
cd apps/server
uv run --extra dev pytest tests/unit/test_cabinet_web_shell.py tests/integration/test_meeting_deletion_workflow.py
```

## Runtime Proof

1. Open `/meetings` with an owner session.
2. Select one row.
3. Confirm the selection toolbar shows Russian count, disabled download, and delete.
4. Activate disabled download and confirm no download starts.
5. Cancel delete and confirm the row remains.
6. Delete one row and confirm it leaves the active list, the page stays on the list, and no report link or report page appears.
7. Select several rows, delete them, and confirm every accepted row disappears while any failed row remains visible with a short Russian error.
8. Repeat through `/desktop/meetings`.

The detailed deletion report remains a separate diagnostic path and is not an expected step in the owner flow.

Evidence must be metadata-only. Do not commit raw audio, transcript text, credentials, cookies, tokens, signed URLs, object keys, private account identifiers, or private local paths.
