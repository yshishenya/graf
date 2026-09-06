# Quickstart: MediaScribe polling recovery

Из корня репозитория:

```sh
cd apps/server
uv run pytest tests/unit/test_processing_recovery.py tests/unit/test_processing_recovery_contracts.py tests/unit/test_processing_temporal_workflow.py
bash scripts/run_local_postgres_tests.sh --focused -q \
  tests/integration/test_mediascribe_processing_happy_path.py \
  tests/integration/test_processing_failures.py
```

Сценарии: pending job остаётся recoverable; `ready` импортируется без нового
submit; provider `failed` показывает terminal recovery; retryable HTTP error
сохраняет same-job polling; watchdog оставляет ручную проверку; transcript
скрыт до diarization, а summary имеет независимый статус; скрытое окно не
теряет detail polling и обновляется при terminal `no_recognizable_speech`.

Для media recovery дополнительно проверить exact subprocess contract ручной
загрузки: source probe `1`, source full decode `0`, tolerant transcode с
`-t 14401` `1`, output probe `1`, strict output decode `1`. Входная длительность
finite/positive/known/≤4h; выявляемое stream/container/revision расхождение и
потеря хвоста сверх малого явного tolerance отклоняются. Для `manual_upload`
MediaScribe получает exact canonical M4A один раз, original media не
отправляется. First-party mixed capture сохраняет `single_wav_v1` и отправляет
canonical WAV; historical dual-track остаётся compatibility-only. Existing
capture, copy/remux и other single-source pass counts не меняются.
При ambiguous response допускаются несколько exact same-key HTTP attempts,
но ровно один provider job; новый key/job разрешён только после подтверждённого
terminal provider outcome и явного нового business attempt.

Worker-owned DB/sessionmaker/storage/HTTP clients переиспользуются между
activities и закрываются только после остановки всех sibling workers. Historical
lineage compatibility остаётся только в read/replay путях.

```sh
cd apps/server
uv run pytest tests/unit/test_processing_temporal_workflow.py
bash scripts/run_local_postgres_tests.sh --focused -q \
  tests/integration/test_playback_normalization_media_matrix.py \
  tests/integration/test_manual_media_upload.py \
  tests/integration/test_mediascribe_processing_happy_path.py \
  tests/integration/test_processing_failures.py \
  tests/integration/test_processing_worker_restart.py \
  tests/contract/test_processing_status_contract.py \
  tests/contract/test_cabinet_static_assets_contract.py
```

Обязательная матрица:

- valid и corrupt-but-recoverable manual input → canonical M4A → один provider POST;
- first-party `single_wav_v1` → canonical WAV без manual M4A gate;
- timeout-after-egress → несколько одинаковых POST attempts с одним key/fingerprint
  и всё ещё один provider job;
- no-audio/truncated/terminal normalization → ноль provider POST;
- normalization retry → countdown + manual due-now без параллельного transcode;
- worker restart до Temporal start и после publication → deterministic recovery;
- ambiguous/running/closed duplicate Temporal start и bounded history → без
  второго provider job, replay current history проходит;
- `archive_audio=false` → нет плеера/storage usage, source и canonical purged;
- provider input-audio failure → terminal projection, frontend polling stopped;
- pending → `no_recognizable_speech` → одна отправка и terminal recovery даже
  если окно было скрыто во время плановой проверки;
- transcript скрыт до diarization, summary независим;
- multipart `audio/mp4` + `manual-media.m4a`.

Repository gate перед PR:

```sh
infra/scripts/ci-local.sh --fast
```

Historical pre-audit evidence 2026-08-27 (не является current-SHA evidence после
исправлений повторного аудита):

- changed-file Ruff, Python compile, JavaScript syntax и `git diff --check` — PASS;
- normalization worker unit — `13 passed`;
- post-fix normalization/deletion/backfill/RLS PostgreSQL matrix —
  `49 passed` + `3 passed`;
- `infra/scripts/ci-local.sh --fast` — `1300 passed`, lint/compile/PASS;
- exact manual subprocess contract, one canonical provider POST, Temporal
  replay/continue-as-new, double cancellation и sibling-worker cleanup входят в
  обязательную current-SHA matrix ниже; pre-sync evidence не заменяет её.

После scoped/current-SHA validation выполнить уже одобренные PR/review/merge,
release/deploy и production E2E. Full CI повторно не запускать; repository
deployment gates и exact-SHA guard обязательны.
