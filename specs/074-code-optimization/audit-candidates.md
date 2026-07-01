# Audit Candidates: Code Optimization

## Baseline

Runtime LOC baseline from 2026-07-01 fresh `origin/master`:

- Python: 35,847
- Swift: 53,152
- Shell: 5,196
- Runtime Python/Swift/shell files: 416

## First Batch: Server Private Helpers With Zero References

Evidence command:

```sh
python3 - <<'PY'
from pathlib import Path
import ast, subprocess
roots=['apps/server/src','apps/server/tests','apps/macos','infra','scripts']
for p in Path('apps/server/src/twobrain_rec_server').rglob('*.py'):
    tree=ast.parse(p.read_text())
    for node in tree.body:
        if isinstance(node,(ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name.startswith('_') and not (node.name.startswith('__') and node.name.endswith('__')):
            res=subprocess.run(['rg','-n',node.name,*roots], text=True, capture_output=True)
            refs=[l for l in res.stdout.splitlines() if not (str(p) in l and (f'def {node.name}' in l or f'class {node.name}' in l))]
            if len(refs)==0:
                print(f'{p}:{node.lineno}:{node.name}')
PY
```

Result:

- `delete now`: `apps/server/src/twobrain_rec_server/cabinet/view_models.py:1009`
  `_event_has_meeting_link_or_location`
  - Direct search: only the definition appears across `apps/server/src`,
    `apps/server/tests`, `apps/macos`, `infra`, and `scripts`.
  - Risk surface: cabinet view model, no route or template registration.
  - Validation: cabinet/view-model focused tests plus full local CI.
- `delete now`: `apps/server/src/twobrain_rec_server/outcomes/service.py:149`
  `_load_current_available_set`
  - Direct search: only the definition appears across runtime/tests/scripts.
  - Risk surface: outcomes service; helper is a one-line alias to the real
    `_load_current_outcome_set`.
  - Validation: outcomes/server tests plus full local CI.
- `delete now`: `apps/server/src/twobrain_rec_server/auth/providers/base.py:472`
  `_first_response_item`
  - Direct search: only the definition appears across runtime/tests/scripts.
  - Risk surface: auth provider parsing; private helper has no callers.
  - Validation: auth provider tests plus full local CI.

## Kept Intentionally

- All one-reference private helpers from deletion, ingest, cabinet, auth,
  calendar, and support code are kept. They have active local callers and often
  encode safety or readability boundaries.

## Deferred

- Swift/macOS large-file cleanup is deferred until a separate Swift-focused
  evidence pass because many symbols are connected through SwiftUI, tests, and
  package targets.
- Dependency removal is deferred until direct package/import evidence is built.
