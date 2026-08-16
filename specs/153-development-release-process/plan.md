# Implementation Plan: Процесс от разработки до релиза

**Branch**: `151-settings-product-surface` | **Date**: 2026-08-16 | **Spec**: [spec.md](spec.md)

## Summary

Уточнить канонический процесс в `docs/agent-guidance/release-and-validation.md`:
focused checks во время разработки, fast lane перед PR, full lane для release
candidate и обязательный full gate на pinned SHA внутри production execute.
Добавить decision rule, release closeout и changelog entry. Runtime-код,
команды CI/CD и GitHub Actions не меняются.

## Technical Context

**Language/Version**: Markdown и shell-команды существующего репозитория

**Primary Dependencies**: `infra/scripts/ci-local.sh`,
`infra/scripts/cd-remote.sh`, текущая Spec Kit guidance

**Storage**: N/A

**Testing**: Markdown review, `git diff --check`, command/reference consistency

**Risk / Validation Lane**: significant-feature — изменение governance/release
правил, без runtime-изменений

**Release Gate**: no deploy — production execution не требуется для изменения
документации

**Target Platform**: macOS developer workflow и production deployment workflow

**Project Type**: self-hosted desktop + server product

**Performance Goals**: не добавлять обязательный full CI на каждый локальный edit

**Constraints**: не ослаблять exact-SHA, approval, smoke, rollback, signing и
notarization gates; не затрагивать незакоммиченные изменения Feature 152

**Scale/Scope**: два канонических guidance-документа, changelog и Spec Kit
артефакты этой feature

## Constitution Check

Pass.

- Соблюдается Spec-Driven Delivery: есть spec, plan, checklist, tasks и
  analyze evidence.
- Не меняются capture, auth, privacy, storage, runtime, secrets или deploy
  behavior.
- Сохраняются exact-SHA, public macOS signing/notarization и explicit approval
  requirements.
- Evidence остаётся metadata-only.

## Validation Plan

1. Проверить, что guidance явно описывает focused → fast → full → execute.
2. Проверить, что после нового commit full evidence инвалидируется.
3. Проверить, что dry-run и explicit approval стоят перед execute.
4. Запустить `git diff --check` и вручную сверить команды с текущими скриптами.
5. Не запускать `ci-local.sh --full`: runtime-код и CI implementation не меняются;
   full lane остаётся release/deploy gate для продукта.

## Project Structure

```text
docs/agent-guidance/release-and-validation.md  # canonical process rules
CHANGELOG.md                                   # Unreleased documentation note
specs/153-development-release-process/         # traceability artifacts
```

**Structure Decision**: Один канонический operational guidance-документ и одна
короткая changelog-запись; отдельный новый скрипт или workflow не нужен.

## Complexity Tracking

Не требуется: решение использует существующие команды и правила.
