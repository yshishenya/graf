# Implementation Plan: Быстрая загрузка файлов через production edge

**Branch**: `codex/192-http2-upload-throughput` | **Date**: 2026-08-23 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/192-http2-upload-throughput/spec.md`

## Summary

Закрепить в репозиторной Nginx-конфигурации уже проверенное production-исправление HTTP/2 upload throughput: увеличить bounded preread window тела запроса с default 64 КБ до 2 МБ. Сохранить существующий server-mediated путь через GRAF API, установочный rollback и все security/storage boundaries. Прямой upload в MinIO и новый upload-протокол не нужны.

## Technical Context

**Language/Version**: Nginx configuration; Bash installer with `set -euo pipefail`

**Primary Dependencies**: Existing Nginx HTTP/2 module and `infra/scripts/install-billing-webhook-edge.sh`

**Storage**: Existing MinIO and PostgreSQL path, unchanged

**Testing**: Focused source assertion, shell syntax check, installer dry-run where a valid local secret fixture is available, production `nginx -t`/reload/health evidence, real WKWebView upload evidence, `infra/scripts/ci-local.sh --fast`

**Risk / Validation Lane**: `high-risk-feature` — repository source controls production edge configuration and can affect all upload traffic; clarification, infrastructure checklist, full artifact analysis and repository validation are required despite the one-line runtime change

**Release Gate**: No additional production deploy in this slice; the exact setting is already live and validated. Repository persistence is required before any future installer execution. A later deploy must keep the existing installer backup, `nginx -t`, reload probes and automatic rollback.

**Target Platform**: Production Linux Nginx edge for `rec.2brain.pro`

**Project Type**: Self-hosted web service with macOS embedded client

**Performance Goals**: A roughly 40 МБ real-client upload over RTT around 165 ms completes transfer in at most 15 seconds and at no less than 30 Mbit/s; HTTP/2 reaches at least 80% of the control HTTP/1.1 throughput on the same path

**Constraints**: Keep server-mediated upload and current API/security limits; add at most 2 МБ preread buffer per active HTTP/2 request stream; no presigned URLs, CORS expansion, custom chunk scheduler, dependencies, schema changes or protocol redesign

**Scale/Scope**: One existing Nginx site source file and one changelog entry; no application code, data model or interface contract changes

## Constitution Check

*GATE: Passed before research and re-checked after design.*

- **Capture-first integrity**: Pass. Capture and local recording behavior are untouched; only post-capture transfer throughput changes.
- **Visible consent and control**: Pass. Recording controls and consent behavior are untouched.
- **Data boundary and secret discipline**: Pass. Audio remains server-mediated through authenticated GRAF API; no desktop credentials, signed URLs or direct MinIO access are introduced.
- **Deletion truth and lifecycle accounting**: Pass. No storage entities, retention or deletion semantics change.
- **Operational safety**: Pass. The existing installer continues to back up config, run `nginx -t`, reload, probe health and roll back automatically.
- **Public macOS distribution integrity**: Pass. No app package, signing or update artifact changes.

Post-design re-check: passed with the same result. `data-model.md` confirms no entity or lifecycle change; no external contract artifact is required.

## Validation Plan

1. Assert `http2_body_preread_size 2m;` is present exactly once in the TLS server block of `infra/nginx/rec.2brain.pro.conf` beside the existing bounded upload-size policy.
2. Run `bash -n infra/scripts/install-billing-webhook-edge.sh` and a safe `--dry-run` when a valid secret fixture is available; do not expose or persist secret content.
3. Run `git diff --check` and `infra/scripts/ci-local.sh --fast`.
4. Reconcile source with completed production evidence: `nginx -t` passed, reload preserved the master PID, health/readiness returned 200, and WKWebView request `a69e664c-73f5-4bf5-ae1f-61f4637f1820` returned 202 in 8.219 s.
5. Keep rollback evidence: live backup `/etc/nginx/sites-available/rec.2brain.pro.conf.before-http2-upload-window-20260823T021938Z`; no rollback execution is needed because all probes passed.

## Project Structure

### Documentation (this feature)

```text
specs/192-http2-upload-throughput/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── checklists/
│   ├── requirements.md
│   └── infra.md
└── tasks.md
```

### Source Code (repository root)

```text
infra/nginx/rec.2brain.pro.conf
infra/scripts/install-billing-webhook-edge.sh
CHANGELOG.md
```

**Structure Decision**: Reuse the existing edge source-of-truth and installer. The only behavior change belongs in `infra/nginx/rec.2brain.pro.conf`; the installer already copies that file with safe validation and rollback. No new helper, test framework or configuration layer is justified.

## Complexity Tracking

No constitution violations or complexity exceptions.
