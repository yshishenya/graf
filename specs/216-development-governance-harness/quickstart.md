# Quickstart: Feature 216 governance checks

All commands below are local or read-only unless explicitly marked as a Dev
promotion. Evidence must contain metadata only: command, status, duration,
SHA, manifest IDs and counts. Never save audio, transcript text, credentials or
private meeting content.

## 1. Confirm feature and clean worktree

```sh
git status --short --branch
git rev-parse HEAD
cat .specify/feature.json
.specify/scripts/bash/check-prerequisites.sh --json --paths-only
```

Expected: явно выбранная ветка `codex/216-…`, feature directory
`specs/216-development-governance-harness`, and no user changes overwritten.

## 1a. Confirm Codex instruction scope

Start a fresh Codex run from the repository root and request the loaded
instruction sources. The expected chain is global guidance, this root
`AGENTS.md`, then only any closer nested file. Feature-specific procedures are
read from the active paths below, not copied into root instructions. If the
chain is unexpectedly long, split the guidance before continuing; Codex's
default combined instruction limit is 32 KiB.

Reference: [OpenAI AGENTS.md guidance](https://developers.openai.com/codex/guides/agents-md).

## 2. Validate specification and governance

```sh
rg -n 'NEEDS CLARIFICATION|TODO|\[FEATURE|\[###' \
  specs/216-development-governance-harness || true
python3 scripts/check_spec_kit_governance.py --self-test
python3 scripts/check_spec_kit_governance.py
```

Expected: no unresolved markers and positive/negative governance fixtures pass.

## 3. Verify Feature ID and issue linkage

```sh
git branch -a --list '*216*'
gh issue view 6090 --repo yshishenya/graf --json number,title,labels,url
gh issue list --repo yshishenya/graf --search '"[216]" in:title' --limit 100
```

Expected: one umbrella reservation, no duplicate active claim, and labels
`feature:216`, `priority:P0`, `area:docs/governance`, `type:hardening`.

## 4. Изолированные проверки Dev harness

```sh
python3 -m pytest -q \
  tests/governance/test_dev_harness.py \
  tests/governance/test_dev_promotion_transaction.py
```

Эти тесты создают отдельные временные каталоги и проверяют manifest, общий SHA,
конкурентную блокировку, частичный отказ и rollback. Они не продвигают
искусственный manifest в общий Dev-стенд. Читающие `status`/`smoke` не требуют
флага dry-run; изменяющие состояние операции должны его поддерживать.

Реальная приёмка установленного приложения, разрешений и работающих компонентов
отдельна: сначала сверить действующие доказательства F229/F249, для оставшихся
пунктов прочитать `docs/agent-guidance/local-development.md` и использовать
единственную `/Applications/GRAF Dev.app`. Отсутствие такого доказательства
не позволяет закрыть T036/T047 по результатам искусственных тестов.

## 5. Dev app identity

```sh
sh apps/macos/Scripts/validate-no-legacy-audio-driver.sh
infra/scripts/dev-harness.sh status --json
```

`status` — читающий снимок установленного `/Applications/GRAF Dev.app` и
активного manifest, а не доказательство сохранения разрешений при обновлении.
Для этого сначала сверяются принятые результаты F229/F249; оставшиеся реальные
сценарии выполняются только по `docs/agent-guidance/local-development.md`.
Исторический `validate-macos-permission-retention.sh` без подкоманды выводит
справку с кодом 0, а его проверки привязаны к production bundle ID; поэтому
он не служит проверкой единственного GRAF Dev и здесь не запускается.

When a local build is intentionally run, use only the existing Dev scripts with
a loopback origin. Verify `pro.2brain.graf.dev`, the same designated requirement
and atomic replacement; do not run public release/notarization commands here.

## 6. Проверки PR и механизма выпуска

```sh
python3 -m pytest -q \
  tests/governance/test_ci_evidence_producer.py \
  tests/governance/test_release_candidate.py
python3 scripts/validate-pr-checks.py --help
```

Для готового PR вызвать общий валидатор по его справке: обязательны GitHub
`governance-fast`, `macos-pr`, `pr-metadata` на точном PR SHA и проверенной
основе. Указать команды, область, результат и пропущенные проверки.
Локальные `infra/scripts/ci-local.sh --fast` / `--full` — диагностика.
Один GitHub `release-full` относится к замороженному кандидату выпуска.

Изолированные тесты проверяют хэши реальных тестовых файлов, неизменяемость
кандидата, решения и отдельной записи публикации. Они не публикуют продукт
и не служат доказательством реального tag/GitHub Release/CD.

## 7. Changelog and legacy checks

```sh
python3 scripts/validate-changelog-fragments.py
python3 scripts/validate-legacy-impact.py \
  --feature specs/216-development-governance-harness/spec.md
```

Expected: Feature 216 owns one fragment, the root changelog is untouched during
feature work, Legacy Impact is present, and no exception is expired or ownerless.

## 8. Reusable harness sample project

The generic core is published at
`https://github.com/yshishenya/graf-development-harness/releases/tag/v0.1.15`.
Clone that immutable tag into a clean temporary directory, confirm commit
`8f41a53508d0c8ca27afb97cea4b020ae474c6ce` against `harness/harness.lock.json`,
and run from the external repository root:

```sh
shellcheck bin/harness-check
PYTHONDONTWRITEBYTECODE=1 bin/harness-check --self-test
(cd sample && PYTHONDONTWRITEBYTECODE=1 ../bin/harness-check --spec specs/001-example/spec.md)
PYTHONDONTWRITEBYTECODE=1 bin/harness-check --package-root .
PYTHONDONTWRITEBYTECODE=1 bin/harness-check --context-check . --package-root .
```

Record the release tag, commit SHA, tool versions and pass/fail counts. This
step must not include GRAF credentials, private paths or meeting content.
Also verify published package checksums, install into a temporary consumer,
and check upgrade/rollback against `v0.1.14`. Keep only logs and checksums;
remove temporary checkouts, packages and environments after verification.

## Release-candidate boundary

Only after all feature tasks, reviewer checklists and convergence are complete:

1. prepare a CalVer candidate and review the assembled Russian changelog;
2. freeze the exact SHA and metadata digest;
3. run one authoritative Full CI;
4. run CD dry-run and obtain explicit approval before any production execute;
5. publish tag/GitHub Release and retain metadata-only evidence.
