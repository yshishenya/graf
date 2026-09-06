# Requirements Checklist: Feature 204

- [X] Scope ограничен terminal no-speech admission/projection.
- [X] Существующие quota, deletion, source и idempotency fences явно сохранены.
- [X] Acceptance scenarios покрывают до- и после-состояние новой попытки.
- [X] Production smoke отделён от локального CI и требует exact SHA.
- [X] Out of scope не включает автоматический retry no-speech или новый сервис.
