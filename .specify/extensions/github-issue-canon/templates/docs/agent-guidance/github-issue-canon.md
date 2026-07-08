<!-- managed-by: github-issue-canon -->

# GitHub Issue Canon

This repository uses GitHub Issues as the execution backlog that mirrors Spec
Kit tasks. Every issue created manually, by an agent, or through
`$speckit-taskstoissues` must follow this canon unless the user explicitly asks
for a one-off scratch issue.

Project path:

```text
docs/agent-guidance/github-issue-canon.md
```

All issue titles, issue bodies, PR descriptions, status comments, closure
comments, and sync notes must be written in Russian by default. Use simple,
clear language that is understandable to non-technical teammates, not only
engineers.

## Title Format

Use this exact format, with the outcome written in Russian:

```text
[{feature}][{priority}][{area}] T###: {русский результат}
```

Examples:

```text
[012][P0][ingest/finalize] T119: Отклонять несовпадающие manifest до finalize
[012][P1][infra/compose] T132: Не запускать production с dev defaults
```

Rules:

- `{feature}` is the three-digit Spec Kit feature number, e.g. `012`.
- `{priority}` is `P0`, `P1`, `P2`, or `P3`.
- `{area}` is a compact ownership/scope tag.
- `T###` is the task id from `tasks.md`; use the first task id in the title
  when an issue covers several tasks, and list every task in the body context.
- The text after `T###:` states the desired outcome in Russian and in plain
  language.
- Do not use emoji, urgency words, all-caps shouting, or repeated punctuation.
- Do not prefix with `bug:`/`feature:` when the same meaning belongs in labels.

## Task-To-Issue Skill Compatibility

If a generic `$speckit-taskstoissues` instruction says to title issues as
`T001: <description>`, that instruction is not the repository template. It is
fallback guidance for repositories without a project canon. In repositories that
install this extension, this canon is the single authoritative template and
overrides the generic title instruction.

For Spec Kit task-backed issues, keep the task id as one standalone token in the
canonical title:

```text
[093][P1][docs] T001: Проверить артефакты фичи перед реализацией
```

Do not create bare `T001: ...` titles in repositories using this canon. Also
include the same task id in body context as `Spec tasks: T001`. This keeps
deduplication stable without copying the whole canon into the general skill.

For a manually created Spec Kit issue that is not tied to one `tasks.md` row yet,
use `T000` only as a temporary triage marker and replace it with a real task id
before closing the issue.

## Body Format

Use Russian sections in this exact order.

```markdown
## Кратко

Одно-два предложения: что должно стать правдой.

## Контекст

- Фича: `012-server-ingest-foundation`
- Приоритет: `P1`
- Область: `ingest`
- Spec tasks: T119, T132
- Источник: review / analyze / implementation / user report / production incident
- Гейт: blocks PR / blocks deployment / follow-up / nice-to-have
- Связанные issues: #123, #124

## Проблема

Что сейчас не так, какой риск есть, и почему это важно для проекта или
пользователя.

## Проверенные факты

- Проверенный факт или найденный gap.
- Какого proof/test сейчас не хватает.
- Что будет плохо, если оставить как есть.

## Границы задачи

Входит:
- ...

Не входит:
- ...

## Критерии приемки

- [ ] Given ..., when ..., then ...
- [ ] ...

## Что проверить перед закрытием

- [ ] Test file or command.
- [ ] Contract/checklist/compose/manual smoke evidence.
- [ ] Documentation/status update if required.

## Заметки по реализации

Ограничения, важные пути, порядок работ и известные ловушки. Пиши практично,
не превращай issue в полный design document.

## Ссылки

- Spec:
- Plan:
- Tasks:
- Связано:
```

## Labels

Use labels as metadata; do not duplicate all metadata in the title.

Required label families for Spec Kit issues:

- `feature:<number>`: e.g. `feature:012`
- `priority:P0`, `priority:P1`, `priority:P2`, or `priority:P3`
- `area:<name>`: e.g. `area:ingest`, `area:auth`, `area:infra`
- `gate:<name>` when applicable: `gate:pr-blocker`, `gate:deployment-blocker`
- `type:<name>`: `type:bug`, `type:hardening`, `type:docs`,
  `type:test-gap`, or `type:feature`

## Pull Request Rules

- Use a pull request template when the repository has one.
- The PR description must include a Russian summary, selected risk/validation
  lane, validation evidence, and issue links.
- When a PR uses a low-risk lane, explain why broader repository or deployment
  gates were not required.
- Use `Fixes #123`, `Closes #123`, or `Resolves #123` only when the PR fully
  satisfies every acceptance criterion for that issue.
- Use `Refs #123` or `Part of #123` when the PR is partial, preparatory, or
  only related.
- If a PR closes multiple issues, list every closing keyword explicitly.
- Closing keywords are reliable only when the PR targets the repository default
  branch. If the PR targets another branch, do not rely on auto-close.

## Closing Rules

- Close an issue only when every acceptance criterion is met or explicitly
  marked not applicable with a reason.
- Do not close a security/privacy/durability issue without validation evidence
  recorded in the PR or the feature quickstart/status docs.
- When an issue maps to Spec Kit tasks, mark matching tasks `[X]` in `tasks.md`
  only after implementation and validation are complete.
- Before closing, add a detailed Russian closure comment that explains what was
  done, why it matters, how it was checked, what is out of scope, and which PR
  and Spec Kit task it closes.
- If GitHub auto-closes the issue after merge, add the detailed closure comment
  immediately after merge if it is missing.
- For duplicates, comment `Duplicate of #123` and explain in Russian why the
  other issue is the source of truth.
- For `not planned` closures, explain in Russian why work will not continue and
  whether a follow-up issue exists.

Required closure comment format:

```markdown
Готово.

Что закрыто:
- ...

Почему это важно:
- ...

Как проверено:
- ...

Что не входит:
- ...

Связи:
- Spec task: T...
- PR: #...
```

## Automation And Spec Kit

- `$speckit-taskstoissues` must create issues using this canon, including the
  `T###:` task id in the title.
- The `github-issue-canon` Spec Kit extension installs this file under
  `docs/agent-guidance/`, issue forms, labels, and validation hooks.
- Do not patch globally installed Spec Kit skills to enforce this rule; they may
  be overwritten by Spec Kit updates.
