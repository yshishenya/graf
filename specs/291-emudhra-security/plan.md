# Implementation Plan: F291 eMudhra

**Branch**: `291-emudhra-security` | **Date**: 2026-10-23 | **Spec**: [spec.md](spec.md)

## Summary

Обновить certifi точечно, экспортировать production constraints, обновить Node 22 в CI, штатно обновить системные CA при сборке. Поведение и данные приложения не меняются.

## Technical Context

Python 3.13, uv, Requests/HTTPX, Node 22, Debian bookworm Docker. Storage: существующие Postgres/MinIO/Temporal без изменений. Testing: pytest governance + lock/export checks + image/client acceptance.

**Risk / Validation Lane**: high-risk-product; security dependencies and infrastructure. Затем release-deploy.
**Release Gate**: reviewed PR + exact governance-fast/macos-pr/pr-metadata; one authoritative release-full на frozen candidate; train/decision + CD dry-run; execute только при всех backup/restore/secret/smoke gates.
**Target Platform**: существующий Linux production 2brain.dev.
**Performance Goals**: без изменения производительности; ограничение каждого TLS-запроса 15 секунд.
**Constraints**: не менять trust policy вручную, TLS, данные, права, DNS/VPN, аналитику; не запускать финансовые/сторонние SMTP-тесты.
**Scale/Scope**: server lock, constraints, CI Node и Docker CA package; никаких новых API/миграций.

## Constitution Check

Pre-research: PASS. Сохраняются owner-controlled egress, секреты, существующие backup/restore/rollback gates, явное production-разрешение. Нет изменений capture/privacy/storage/AI route contracts. Post-design: PASS; FR-007 блокирует execute до применимого разрешения backup, не разрешает обход.

## Validation Plan

См. quickstart.md. Рецензент проверяет reviewer-owned security/infra checklist до tasks/implementation. Анализ spec/plan/tasks: ноль unresolved critical/high. Issue sync до implementation. Converge перед PR. Production readback включает API/processing/media/maintenance версии, CA-пакет и HTTP-клиенты. Обычный HTTPS-контроль отличает отключение сети от TLS rejection. Сохранить metadata-only receipt.

## Project Structure

- `apps/server/uv.lock`, `apps/server/constraints.txt`, обязательный минимальный certifi security floor в `apps/server/pyproject.toml`.
- `.github/workflows/release-full.yml`, `.github/workflows/governance-fast.yml`, `tests/governance/test_governance_workflow.py`.
- `infra/server/Dockerfile`: штатное пакетное обновление ca-certificates перед разделением runtime/media.
- `changes/unreleased/F291.yaml`; эта папка спецификации.

## Complexity Tracking

Новых абстракций, сервисов, хранилищ и исключений нет. Existing lock/export и release scripts используются напрямую.
