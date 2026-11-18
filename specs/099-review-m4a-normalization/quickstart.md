# Quickstart: Review M4A Normalization

**Feature**: `099-review-m4a-normalization`

## Purpose

Prove that every supported valid accepted source reaches one canonical playable
M4A automatically, without user/admin repair, while impossible inputs terminate
honestly and transient system failures recover by themselves. Evidence covers
new first-party recordings, manual uploads, legacy backfill, resource limits,
restarts, deletion races, tenant/privacy boundaries, browser/embedded playback,
release/deploy, production E2E, and cleanup.

The standalone feature-097 Codex Security scan remains deferred and untouched.
The authorization, RLS, subprocess isolation, redaction, and deletion tests below
are ordinary feature acceptance gates and must not be presented as completion
of that scan.

## Prerequisites

- Active clean 099 worktree anchored to current `origin/master`.
- Feature artifacts complete: spec, plan, research, data model, contracts,
  requirements/media/lifecycle checklists, tasks, and clean analyze result.
- Docker available for media target and disposable PostgreSQL/MinIO/Temporal.
- Python/server dependencies resolved through `uv`.
- Swift 6/Xcode toolchain for unchanged macOS regression tests.
- Chrome and embedded macOS cabinet available for real playback/seek checks.
- Authorized source recordings only from the operator-provided
  `$GRAF_TEST_REC_DIR`; originals remain read-only.
- Synthetic format/edge fixtures are generated inside a feature temp directory
  or disposable media container and deleted after the run. No raw audio is
  committed.
- Evidence contains only aliases, format, size/duration buckets, state/reason,
  counts, timestamps, artifact availability, versions, and cleanup result.

## 1. Spec and prerequisite gate

```sh
.specify/scripts/bash/check-prerequisites.sh --json --paths-only
git diff --check
```

Expected:

- feature directory is exactly `specs/099-review-m4a-normalization`;
- branch/feature anchor agree;
- no unresolved critical analyze/checklist finding;
- no placeholder or planning clarification remains;
- no unrelated dirty files are included.

## 2. Unit state, probe, profile, and read-model checks

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/unit/test_playback_normalization_profile.py \
  tests/unit/test_playback_normalization_bmff.py \
  tests/unit/test_playback_normalization_selection.py \
  tests/unit/test_playback_normalization_state.py \
  tests/unit/test_playback_normalization_retry.py \
  tests/unit/test_playback_normalization_audit.py \
  tests/unit/test_artifact_egress_view_models.py \
  tests/unit/test_cabinet_view_models.py \
  tests/unit/test_cabinet_web_shell.py
```

Required assertions:

- canonical AAC-LC/48 kHz/mono/bitrate/start/duration/size/box rules;
- BMFF rejects overflow/truncation/`moof`/missing atoms/wrong order;
- one usable stream and unique-default selection; no first/highest-channel guess;
- explicit first-party 50/50 aligned longest-duration mix arguments;
- job/attempt/backfill state transition validation;
- four-attempt cycle and 15m/1h/6h/24h/daily cooldown due times;
- deletion/read access precedence;
- transcript/playback independent combinations;
- strict audit allowlist and forbidden filename/path/key/stderr/content values;
- no user/admin retry action in projections.

## 3. Exact media-container capability gate

Build and run the media-only target through the project script added by this
feature:

```sh
infra/scripts/test-playback-normalization-container.sh
```

The script must generate disposable synthetic silence/tone fixtures inside the
container, never commit them, and prove:

| Input | Expected result |
|---|---|
| WAV PCM | canonical transcode + full decode |
| MP3 | canonical transcode + full decode |
| raw AAC | canonical transcode + full decode |
| FLAC | canonical transcode + full decode |
| Ogg/Vorbis | canonical transcode + full decode |
| Ogg/Opus | canonical transcode + full decode |
| canonical M4A fast-start | strict reuse/copy path |
| canonical AAC M4A with `moov` after `mdat` | lossless fast-start remux |
| MP4 with AAC audio | selected-audio transcode, video excluded |
| MOV with PCM/AAC audio | selected-audio transcode, video excluded |
| M4V | selected-audio transcode |
| WebM/Opus | selected-audio transcode |
| MKV supported audio | selected-audio transcode |

It must also prove:

- pinned FFmpeg/FFprobe version and build configuration;
- AAC encoder/`aac_low`, `ipod` muxer, supported demuxers/decoders;
- `+faststart` produces `moov < mdat` and no `moof`;
- explicit `-map` produces exactly one audio stream and no others;
- non-file protocol input is refused;
- metadata/chapters are stripped;
- 128 MiB cap, stdout/stderr caps, timeout and process-group cancellation;
- container user is non-root and work files are private;
- synthetic fixture/work directory cleanup leaves residue zero.

## 4. Ingest, workflow, idempotency, and API contracts

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/contract/test_playback_normalization_contract.py \
  tests/contract/test_playback_status_contract.py \
  tests/contract/test_playback_normalization_no_secret_egress.py \
  tests/contract/test_ingest_openapi_contract.py \
  tests/contract/test_openapi_contract_drift.py \
  tests/integration/test_playback_normalization_finalize.py \
  tests/integration/test_playback_normalization_workflow.py \
  tests/integration/test_playback_normalization_idempotency.py \
  tests/integration/test_finalize_processing_autostart.py \
  tests/integration/test_manual_media_upload.py \
  tests/integration/test_ingest_happy_path.py
```

Required assertions:

- finalize accepts required first-party roles with or without optional playback;
- playback candidate is checksum-verified but hidden/unvalidated;
- candidate digest is excluded from immutable source fingerprint;
- manual upload source remains role `media` and separate;
- normalization job is created in the accepted-source transaction;
- accepted source commits before normalization/MediaScribe external dispatch;
- normalization does not depend on `processing_enabled` or result import;
- lost immediate dispatch is picked up within 60 seconds;
- deterministic workflow identity contains only revision UUID/profile;
- duplicate finalize/start/pickup/retry returns the same job/record;
- two workers converge to one active canonical artifact;
- generated output is invisible until validation+publication commit;
- OpenAPI/read projection contains no repair mutation endpoint.

## 5. Real format and failure integration matrix

Run the media-enabled integration suite in its disposable container environment:

```sh
infra/scripts/test-playback-normalization-integration.sh
```

Required scenarios:

| Scenario | Expected durable/read result |
|---|---|
| Valid supported audio/video matrix | `ready`, one full-decoded profile-v1 artifact |
| Wrong extension, valid bytes | detected by bytes and succeeds when matrix-supported |
| Supported extension, wrong bytes | terminal `corrupt_source` |
| Empty file | terminal `empty_source` |
| Video-only | terminal `no_audio` |
| Album art only | terminal `no_audio` |
| One usable stream among unusable streams | selected unique usable stream |
| Multiple usable, one default | selected unique default |
| Multiple usable, no default | terminal `ambiguous_audio_tracks` |
| Multiple usable, several defaults | terminal `ambiguous_audio_tracks` |
| Selected default decode fails | terminal corrupt; no fallback stream |
| Unsupported codec/container | terminal unsupported |
| Encrypted media | terminal encrypted/unsupported |
| More than 16/8 streams | terminal stream limit |
| Actual duration over 4 hours | terminal duration limit, never truncated ready |
| Final output over 128 MiB | no publish; bounded failure |
| Fully canonical M4A | byte-copy/promote after complete decode |
| Non-fast-start canonical audio | lossless remux + complete gate |
| Fragmented/truncated-tail M4A | no strict reuse |
| First-party candidate absent/invalid | deterministic dual-source fallback |
| First-party two roles differ in duration | longer aligned timeline, missing tail silence |
| Source digest changes/missing/purged | terminal mismatch/missing, no fabricated media |

Every ready case must run a second full decode of the stored object, not only
inspect database metadata.

## 6. Retry, restart, backfill, and priority gate

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/integration/test_playback_normalization_retry.py \
  tests/integration/test_playback_normalization_restart.py \
  tests/integration/test_playback_normalization_backfill.py \
  tests/integration/test_playback_normalization_priority.py \
  tests/integration/test_playback_normalization_incidents.py
```

Inject and verify:

- temporary MinIO/DB/Temporal/temp-capacity failure;
- worker termination during download, transcode, upload, and publication;
- failure after object upload but before database commit;
- expired lease in `running`, `publishing`, and `cleanup_pending`;
- four attempts exhausted, then automatic 15m/1h/6h/24h/daily cycles;
- generated output canonical-gate failure classified as system/retryable;
- no source re-upload and no user/admin action;
- one deduplicated metadata-only operational incident;
- startup orphan cleanup;
- backfill cursor resume after every page boundary;
- no legacy mutation before the whole run reaches `inventory_complete`;
- new-ingest > due-retry > legacy-backfill priority;
- page 100, batch 25, concurrency 1 limits;
- valid existing artifact preserved; invalid regenerated; missing source terminal;
- titles, source revision, transcript and summary remain unchanged.

## 7. Migration, PostgreSQL uniqueness, locks, and RLS

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/integration/test_playback_normalization_migrations.py \
  tests/integration/test_playback_normalization_postgres.py \
  tests/integration/test_postgres_migrations.py \
  tests/contract/test_rls_policy_matrix_contract.py \
  tests/contract/test_rls_future_table_contract.py
```

```sh
cd ../..
infra/scripts/verify-rec-migration.sh --execute
```

Expected:

- upgrade `0021 -> 0022` and downgrade succeed;
- existing playback rows remain unvalidated and are not arbitrarily trusted;
- partial unique canonical index works on SQLite and PostgreSQL;
- PostgreSQL concurrent publishers yield one winner and cleaned loser;
- meeting row lock makes deletion win publication race;
- new tables force RLS and deny cross-workspace reads/writes;
- only the two narrow normalization maintenance operations are accepted;
- maintenance enumeration cannot read content fields;
- exact tenant worker context owns artifact work;
- migration performs no FFmpeg/MinIO backfill.

SQLite success is not sufficient evidence for PostgreSQL lock/RLS behavior.

## 8. Deletion, retention, temp, and diagnostics

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/integration/test_playback_normalization_deletion.py \
  tests/integration/test_meeting_deletion_workflow.py \
  tests/integration/test_retention_deletion_migrations.py \
  tests/contract/test_retention_deletion_contract.py \
  tests/contract/test_deletion_no_secret_leakage.py \
  tests/contract/test_playback_normalization_no_secret_egress.py
```

Required scenarios:

- deletion during local download/transcode;
- deletion after MinIO attempt upload;
- deletion while DB publisher waits;
- deletion immediately after canonical publish;
- retention deletion while normalization active;
- canonical playback and unpublished attempt reported separately;
- each distinct object deleted once and rows marked purged;
- storage outage fails deletion closed with retryable truth;
- worker losing race cannot republish;
- startup reaper and deletion do not delete an active canonical object twice;
- logs/audit/incidents/reports contain no filename/path/key/stderr/content.

## 9. Cabinet/OpenAPI/accessibility and Range behavior

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/integration/test_cabinet_playback_route.py \
  tests/integration/test_artifact_egress_policy.py \
  tests/integration/test_cabinet_meeting_list.py \
  tests/integration/test_cabinet_meeting_detail.py \
  tests/contract/test_cabinet_contract.py \
  tests/contract/test_cabinet_no_secret_content_egress.py
```

Prove all playback/transcript combinations from the status contract, plus:

- no dead audio element in preparing/unavailable states;
- no retry/reprocess/backfill/contact-admin control or copy;
- localized Russian/English state text;
- stable state across refresh, two tabs, reconnect and app restart;
- access/deletion precedence and no cross-workspace existence leak;
- ready playback returns real decodable `audio/mp4`;
- valid `200`/`206`, `Accept-Ranges`, `Content-Range`, inline filename;
- range body is a stored canonical object and no conversion path runs;
- keyboard/focus/screen-reader semantics, light/dark and narrow/wide layouts;
- browser and embedded routes use the same projection.

## 10. macOS regression gate

No native source change is planned. Run the exact affected regression surface:

```sh
swift test --package-path apps/macos --disable-swift-testing \
  --filter 'CaptureRateAACReviewAudioWriter|SystemAudioRecordingPackage|DesktopUploadClient|DesktopUploadQueue|DesktopCabinetWorkspace|DesktopCabinetUploadLink'
```

Expected:

- required microphone/system/manifest source roles remain unchanged;
- optional playback descriptor remains AAC-LC/48 kHz/mono;
- invalid local optional candidate cannot block required-source upload;
- server, not desktop metadata, owns canonical validation;
- Record/Stop, active capture, one-action Stop and custody remain unchanged;
- embedded cabinet receives no new native repair control;
- desktop still never sends audio directly to MediaScribe.

If implementation changes `apps/macos` after all, expand to full relevant Swift
tests, release build, installer, identity/signing/entitlement/launch checks and
installed-app validation before integration approval.

## 11. `test-rec` local E2E

Inventory only safe aliases/format/size/duration. Copy originals into a
feature-specific temporary directory; never modify originals.

Run complete scenarios:

1. First-party package with the accepted manifest, microphone, system, and
   optional playback candidate -> accepted commit -> automatic validation or
   lossless remux -> ready -> Range play/seek.
2. First-party package without a playback candidate -> automatic deterministic
   dual-source mix -> ready -> Range play/seek.
3. Manual upload canonical M4A -> source retained separately -> automatic
   copy/remux -> ready.
4. Manual upload supported WAV working copy -> automatic transcode -> ready.
5. Transient storage/worker restart injected after acceptance -> same record/job
   recovers automatically.
6. Truncated/corrupt working copy -> terminal reason, no partial playback and no
   retry control.
7. Deletion during work -> cancelled/purged, residue zero.

For speech-bearing authorized scenarios, continue through MediaScribe import and
summary generation and prove playback, transcript, speaker/diarization, and
summary independently. Do not emit their text/content in evidence.

Evidence per scenario:

- safe test alias;
- accepted meeting/revision/job state sequence;
- attempt/retry counts;
- final profile/byte/duration availability only;
- transcript/summary status and counts only;
- browser/embedded canplay/seek result;
- cleanup result and original-preserved check.

## 12. Real Chrome and embedded UI gate

Using authenticated synthetic/local E2E records, verify in Chrome and embedded
macOS cabinet:

- preparing state immediately after acceptance;
- page/tab/app close does not stop work;
- automatic transition to player without repair action;
- play, pause, seek near middle/end, reconnect and refresh;
- transcript ready while playback preparing;
- playback ready while transcript processing/failed;
- terminal no-audio/corrupt/ambiguous safe copy;
- deletion removes/blocks player;
- light/dark, keyboard, focus, narrow/wide and reduced-motion behavior.

Screenshots may support layout review but must contain only synthetic safe data.
Playback success requires browser media events and server Range evidence, not a
screenshot alone.

## 13. Focused lint and canonical local gate

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev ruff check \
  src/twobrain_rec_server/normalization \
  src/twobrain_rec_server/workflows \
  src/twobrain_rec_server/ingest \
  src/twobrain_rec_server/cabinet \
  src/twobrain_rec_server/deletion \
  src/twobrain_rec_server/db \
  tests/unit/test_playback_normalization_*.py \
  tests/contract/test_playback_normalization_*.py \
  tests/integration/test_playback_normalization_*.py
```

```sh
cd ../..
infra/scripts/ci-local.sh
```

After the last code-affecting fix, rerun the full canonical gate. Record exact
HEAD SHA, commands, counts, durations, media-container version, migration/RLS,
benchmark, scenario receipts, diff review, issue reconciliation, and worktree
status.

## 14. Review and integration checkpoint

Before requesting integration approval:

- run product/spec/convergence review;
- architecture/code/Ponytail review;
- untrusted-media/dependency/RLS/privacy/deletion review as normal feature
  acceptance (not the deferred 097 scan);
- QA/UX/accessibility/browser/embedded review;
- test/release-readiness review;
- validate every finding and fix/retest all confirmed Critical/High;
- run `$speckit-converge` until no remaining required task;
- show exact diff, HEAD SHA, full gates, operational risk and rollback.

Commit/push/PR/merge require explicit integration approval for that validated
candidate.

## 15. Release and production closeout

After merge and prepared release plan:

```sh
./scripts/prepare-release.sh YYYY.MM.DD.N
infra/scripts/cd-remote.sh --dry-run
```

Show the exact merged SHA, tag candidate, backup/rollback, migration, media
worker image/version, expected legacy inventory, gate results and risk. Obtain
explicit release/deploy approval before release-prep commit, tag/GitHub Release,
or:

```sh
infra/scripts/cd-remote.sh --execute
```

Production closeout must prove:

- tag/GitHub Release point to merged master SHA;
- backup/restore rehearsal and migration `0022` pass;
- API/processing/media worker/Temporal/MinIO/PostgreSQL health;
- runtime SHA and non-root media-worker resource limits;
- exact FFmpeg capability smoke and zero residue;
- new first-party and manual accepted sources normalize automatically;
- lost dispatch/worker restart recovers without user action;
- legacy run inventories before mutation and bounded backfill advances/drains;
- Chrome and embedded playback canplay/seek with Range;
- transcript/playback statuses remain independent;
- authorized speech scenario reaches transcript/diarization/summary truth;
- deletion race cleans DB/object/temp/test data with residue zero;
- no new critical logs or forbidden metadata;
- tasks, Issues, PR, changelog and current-product-status reconcile with exact
  evidence.

Do not claim feature 099 complete from build, CI, deploy smoke, or worker health
alone. The production user paths, automatic recovery, backfill, browser playback,
and cleanup are required.

## Requirement traceability

| Requirement range | Primary evidence |
|---|---|
| FR-001–FR-007, FR-038 | canonical gate, reuse/remux/transcode, one active artifact |
| FR-008–FR-010 | title/calendar regression and duplicate finalize/idempotency |
| FR-011–FR-017, FR-023–FR-025, FR-040–FR-042 | automatic retry, terminal truth, backfill, no controls |
| FR-018–FR-020, FR-036–FR-037 | deletion/temp/audit/privacy lifecycle |
| FR-021, FR-029–FR-031 | limits, media container, temp, timeout, resource benchmark |
| FR-022, FR-032 | list/review/two-tab and transcript-independent status |
| FR-026–FR-028, FR-033–FR-035 | accepted lineage, no competing service, conflict handling |
| FR-039 | one usable/unique-default stream and ambiguity cases |
| SC-001–SC-022 | scenario receipts, counts, browser Range, production E2E/backfill |

Every completed task and evidence receipt references its covered FR/SC IDs. A
green command without requirement/scenario mapping is not closeout evidence.


## 2026-10-17 — попытка A не затрагивает B

Штатный `apps/server/scripts/run_local_postgres_tests.sh --focused`:
restart, retry, workflow, deletion, incidents, audit persistence, postgres.
Новые restart случаи обязаны сначала воспроизвести RED исходного source,
затем PASS исправления: late exception со старым/повторным owner, B в
local_preparing/uploaded с reservation; delayed job-wide/direct cleanup;
истёкшая lease, READY winner, обычный настоящий отказ каталога.
Проверять неизменность B lease/reason/due/counters/reservation/object и
исходных source bytes; все барьеры bounded, контейнер/temp очищены.
Детерминированные часы/fake pipeline/storage/Temporal не доказывают живое
автоматическое восстановление и post-deploy PASS. Никакой production записи.


## 2026-11-17 — T014/#3361: матрица владения verified-download

Активная узкая проверка FR-029/031/037/045, SC-025 после independent checklist
PASS/analyze/issue sync. Старые media/Dev/production сценарии не повторяются
без нового основания. Импортировать настоящий storage module и настоящие
потребители; подменять только сетевой ответ и точку внедрения отказа. Файлы,
ссылки и descriptor — настоящие, только в собственном `tmp_path`. Проверка
AST от 2026-11-17 остаётся ограниченным RED, не доказательством полного импорта.

| Сценарий | Измеримый результат |
|---|---|
| Existing regular → `EEXIST` | inode/байты/права файла прежние, unlink не вызывается, причина temporary_storage_unavailable |
| Existing symlink → exclusive/no-follow отказ | сама ссылка/readlink и inode/байты/права target прежние, unlink не вызывается |
| До-create `ENOSPC` или `EACCES`, с существующим leaf и без него | прежний leaf сохранён либо новый не возник, descriptor не закрывается как будто получен, ответ закрыт/released |
| Fresh success, маленькие порции и payload больше 4 MiB | точные байты/размер/digest, режим 0600, read запросы положительные и ≤4 MiB по умолчанию; descriptor закрыт, ответ закрыт/released |
| После-create ошибка write или fsync | причина temporary_storage_unavailable, только собственный partial удалён, descriptor закрыт, ответ закрыт/released |
| После-create лишний/короткий payload, превышение max_bytes, неверный digest | причина source_mismatch, собственный partial удалён; те же resource assertions |
| Async wrapper: existing leaf и fresh success | общий sync helper, прежний leaf сохранён/точные байты скачаны; те же причины и ресурсы |
| Оба production consumers через настоящий verified helper | fresh success staging и сохранность existing leaf при отказе; normalization сохраняет StorageTransferError, submit отображает в TempStorageUnavailableError; прежние missing/mismatch mappings покрыты существующими либо focused тестами |
| Ранние invalid input и missing/unavailable transport | прежние причины и отсутствие локальных побочных изменений; источник не модифицируется |

Добавить постоянные регрессионные тесты в
`apps/server/tests/unit/test_playback_normalization_storage.py`, сначала
выполнить их на старом коде (ожидаемый RED из-за existing destination), затем
после минимальной правки весь этот файл и выбранные submit/error tests.
Подмены/границы каждого опыта обозначить в validation receipt. Проверять close
и release раздельно, полученные descriptor через настоящий `fstat` после выхода;
не выдавать фиктивные булевы признаки одного метода за проверку обоих.
Сохранить Ruff, governance/diff, независимый review/converge и exact-SHA PR gates.
Concurrent replacement после open и отказы самой cleanup/close/release этой
матрицей не доказаны. MinIO integration, единственный GRAF Dev и production
этими проверками не затрагиваются и принятыми не объявляются.


## 2026-11-17 — T014: настоящая автоматическая серверная приёмка

Следующий шаг после guard #8128 —
[контракт этапов A/B/C](./contracts/real-transport-acceptance.md).
Исходные §§3–9/11–15 сохраняют полный объём; новые источники соответствуют F275,
без создания старых dual-source upload. Implementation admission выдан после
независимого PASS 120/0, analyze без CRITICAL/HIGH и sync существующего #3361.
Этап A исполнен 2026-11-17; команды ниже — действующий запускатель, B/C
остаются открытыми:

```sh
python3 apps/server/scripts/run_playback_normalization_real_transport.py
```

Он до первого collection проверяет отсутствие `.env`/symlinks, готовые frozen
зависимости и явный локальный Docker socket, CLI checksum, FFmpeg/ffprobe,
локальные image IDs и свободное место; создаёт собственные temp/Docker config,
очищает env и вызывает штатный `run_local_postgres_tests.sh --focused -q -n 0
 acceptance/playback_normalization_real_transport.py` с собственным заранее
записанным PG resource manifest. Точная схема, actual image/label/ID до SQL,
сроки/аварийный handoff и проверки отказов определены в контракте H1.
Прямой pytest с унаследованным окружением не является допустимой командой.

Приёмочный файл находится вне обычного discovery. До A contract tests
отдельно доказывают неизменный ordinary collection/execution без CLI/MinIO,
отсутствие импорта/ресурсов нового опыта и FAIL явного вызова без контекста
до app imports/миграций. Ни skip, ни изменение общей CI selection не нужны.
Новый обычный contract test stdlib-запускателя и существующий runner contract
проверяют H1/H2 на doubles; это не настоящая transport acceptance.
Недостающий evaluation extra/gepa0.1.4 готовится явно до опыта по frozen lock,
проверяется отдельно; автоматической установки при collection нет.

A-success: HTTP202 accepted WAV, автоматический workflow/worker, restricted
media-role, наблюдённый verified source helper, ready canonical, независимые
size/digest/profile/BMFF/full decode скачанного объекта и Range206.
A-corrupt: HTTP202 принятого непустого источника, terminal/corrupt_source,
нет canonical/публикации/повтора, исходник сохранён. Сроки/cleanup обязательны
по контракту; skip/setup failure/иной reason/неполная очистка — FAIL.

Receipt перечисляет только исполненные строки A/B/C и явно все открытые.
Повторно запускать прежние50 guard/общие3132 CIunit без изменения их входов
не нужно. Новый код требует собственных focused/lint/process проверок,
converge/code review и свежих точных SHA/base PR gates. Два A не дают права
закрыть T014/#3361 или заявить production/UI acceptance.
