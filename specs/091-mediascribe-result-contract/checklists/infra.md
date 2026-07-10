# Infra Checklist: MediaScribe Result Contract

- [x] CHK001 MediaScribe network contract changes are limited to existing poll/result endpoints. [Dependency]
- [x] CHK002 The plan preserves existing retry/alert behavior for MediaScribe service-origin failures. [Reliability]
- [x] CHK003 The plan avoids a MediaScribe transcript download call for empty transcripts, preventing expected 409s. [Reliability]
- [x] CHK004 Schema changes are nullable and backward compatible for existing processing rows. [Postgres]
- [x] CHK005 The repository gate is `infra/scripts/ci-local.sh`; production deploy is out of scope. [Release Gate]
- [x] CHK006 Audit/log classifications explicitly distinguish `input_audio_problem`, `mediascribe_service_problem`, and `processed_no_transcript`. [Diagnostics]
