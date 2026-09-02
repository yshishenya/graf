# Implementation Plan: Надёжный GitHub CI для PR

**Branch**: `233-github-actions-runner-bootstrap` | **Date**: 2026-09-02
**Risk / Validation Lane**: significant-feature (governance/CI)

## Summary

Исправить GitHub runner bootstrap для существующего `governance-fast` workflow.
После проверки workflow включить Actions и обязательный status check на уровне
репозитория. Локальный CI не удаляется и остаётся ручным fallback.

## Technical Context

- GitHub Actions, Ubuntu runner, Bash, Python
- Existing `infra/scripts/ci-local.sh`, Spec Kit lock
- Bootstrap release `v0.9.9`, SHA-256 закреплён в workflow
- `specify-cli==1.0.1` соответствует `.specify/speckit-bootstrap.lock.json`

## Constitution Check

- PASS: не затрагивает capture, privacy, auth, storage или production runtime.
- PASS: exact SHA, fail-closed evidence и linear history сохраняются.
- PASS: локальный fallback не удаляется.

## Validation Plan

1. Workflow and governance self-tests locally.
2. GitHub Actions dispatch on exact branch SHA.
3. Verify successful PR check and required branch-protection context.
4. Record operator configuration in issue #6363.
