# spec-kit-ext-linear-sync

Spec Kit extension for syncing feature tasks and GitHub issues into Linear.

The extension is intentionally conservative:

- `tasks.md` remains the implementation source of truth.
- GitHub issues remain the code and PR traceability layer.
- Linear is the day-to-day project board for status, priority, cycle, assignee,
  blockers, relations, project updates, and comments.
- Dry-run is the default. Use `--apply` only after reviewing the planned sync.
- All generated issue and comment text is Russian by default and should be
  understandable to non-technical teammates.
- `sync --apply` creates the Linear Project when it is missing, then creates
  issues inside that project. It must not create projectless issues silently.
- `validate --apply` checks real Linear issue status and project membership.

## Commands

```text
$speckit-linear-init
$speckit-linear-import
$speckit-linear-sync
$speckit-linear-validate
```

The scripts can also be run directly:

```sh
python3 .specify/extensions/linear-sync/scripts/linear_sync.py init
python3 .specify/extensions/linear-sync/scripts/linear_sync.py import --feature 013
python3 .specify/extensions/linear-sync/scripts/linear_sync.py sync --feature 013
python3 .specify/extensions/linear-sync/scripts/linear_sync.py validate --feature 013
```

Use `--apply` to mutate Linear.

## Environment

```sh
LINEAR_API_KEY=...
LINEAR_TEAM_KEY=REC
LINEAR_PRODUCT_NAME="2brain Rec"
LINEAR_PROJECT_TEMPLATE="{product} / {feature} {title}"
```

The sync script also reads these values from the project `.env` file when they
are not already exported in the shell.

The first version creates and validates the local mapping file:

```text
.specify/linear.yml
```

It is safe to commit that file if it contains only identifiers and no secrets.

By default each Spec Kit feature becomes a separate Linear Project whose name
contains both the product and the feature, for example:

```text
2brain Rec / 013 Federated Auth Foundation
```

Use `LINEAR_PROJECT_NAME` only when you want to force one exact existing Linear
project name instead of the product/feature template.
