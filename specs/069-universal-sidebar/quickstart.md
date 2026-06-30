# Quickstart: Universal Cabinet Sidebar

## Prerequisites

- Work from repository root.
- Ensure the active feature is `specs/069-universal-sidebar`.
- Keep unrelated dirty files out of validation decisions.

## Focused Server Validation

Run the cabinet shell-focused suite:

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/unit/test_cabinet_template_sections.py \
  tests/unit/test_cabinet_navigation_model.py \
  tests/unit/test_cabinet_web_shell.py \
  tests/contract/test_cabinet_contract.py \
  tests/contract/test_calendar_settings_contract.py \
  tests/integration/test_cabinet_meeting_list.py \
  tests/integration/test_cabinet_meeting_detail.py \
  tests/integration/test_cabinet_hx_fragments.py
```

Expected result:

- all selected tests pass;
- full cabinet pages contain one shell and one primary sidebar;
- desktop embedded pages contain the compact rail contract;
- fragment responses do not contain `app-shell` or primary sidebar markup.

## Native Boundary Validation

If implementation touches macOS native files again, run:

```sh
swift test --package-path apps/macos --filter DesktopMeetingShellWebViewBoundaryTests --disable-swift-testing
```

Expected result:

- desktop product navigation remains embedded-cabinet-owned;
- native product sidebar symbols remain absent.

## Repository Closeout Gate

Before marking the feature complete or opening a PR:

```sh
infra/scripts/ci-local.sh
```

Expected result:

- server tests pass;
- server lint passes;
- Python compile and existing hardening checks pass.

## Manual Review

Review rendered HTML or browser pages for:

- meetings list and detail use matching sidebar structure;
- settings and calendar settings use the same sidebar structure;
- browser and desktop embedded routes show matching labels and active destinations;
- disabled/future destinations are visible but not active links;
- focus outline is visible and distinct from selected state;
- compact embedded rail remains usable when labels are visually hidden.
