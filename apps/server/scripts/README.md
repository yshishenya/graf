# Server Smoke Helpers

Scripts in this directory support local and production-like 2brain Rec ingest
validation.

Production smoke helpers must use a dedicated internal smoke identity/device,
must not reuse `seed_dev_identity.py`, and must not print live credentials or raw
meeting content.
