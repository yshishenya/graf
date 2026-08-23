# Server Smoke Helpers

Scripts in this directory support local and production-like 2brain Rec ingest
validation.

Production smoke helpers must use a dedicated internal smoke identity/device,
must not reuse `seed_dev_identity.py`, and must not print live credentials or raw
meeting content.

`manage_promo_campaign.py` is an internal billing maintenance helper. It reads a
promo code through a hidden prompt or stdin, stores only its hash, defaults to a
metadata-only dry-run, and requires `--execute` for create/disable writes. Never
put a real code in shell arguments, history, logs or evidence.
