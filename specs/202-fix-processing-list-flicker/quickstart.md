# Quickstart: Проверка стабильных processing-статусов

## Focused regression

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused -q \
  tests/unit/test_cabinet_web_shell.py \
  tests/contract/test_cabinet_static_assets_contract.py \
  tests/integration/test_cabinet_meeting_list.py \
  tests/integration/test_cabinet_hx_fragments.py
```

## Static checks

```sh
node --check apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js
ruff check \
  apps/server/src/twobrain_rec_server/cabinet/rendering.py \
  apps/server/src/twobrain_rec_server/cabinet/view_models.py \
  apps/server/tests/unit/test_cabinet_web_shell.py \
  apps/server/tests/contract/test_cabinet_static_assets_contract.py
```

## Rendered QA

На metadata-only fixture проверить desktop и narrow viewport:

- failed / processing / failed rows сохраняют порядок, текст и высоту;
- повторные projection ticks меняют только central readiness node;
- смешанный processing + uploading/playback progress swap сохраняет видимый
  processing-текст без дополнительного запроса projection;
- terminal transition выполняет один list refresh;
- keyboard focus и selected row сохраняются.

## PR gate

```sh
infra/scripts/ci-local.sh --fast
```

Full CI и deploy выполняются только на отдельном exact-SHA release gate.
