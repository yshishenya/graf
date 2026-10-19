# Независимая проверка F259: точная связь PR и запуска CI

Дата: 2026-10-16. Проверяющий: отдельный агент `review_f259_binding`.
Ветка: `codex/259-ci-proof-binding`, основа
`c6c5441c930b8c1ecffed6de9b80773aa0e757e5`.
Полоса: high-risk-product / significant governance, существующая US3.

Первоначальная проверка: **FAIL gate / 7 подтверждено, 1 не подтверждён** —
отсутствовал task-backed владелец T027–T029. После согласования #7644:
**PASS требований / 8 подтверждено, 0 не подтверждено; CRITICAL 0, HIGH 0**. Архитектурных блокирующих
замечаний к выбранному решению нет. Реализация не проверена и ещё не начата.

## Основания и существенные границы

1. verify_feature_runs уже вызывает _github_pr_checks для каждого точного
PR/head/governance-run, независимо от run API-связи, с checked_prs cache.
Повторный commit lookup не повышает доказательность: коммит действительно
может принадлежать нескольким PR. Общий validate-pr-checks.py через
verify/current_run/current_gate/validate_bundle проверяет идентичность,
текущую попытку, артефакт, jobs, head/base и актуальные метаданные.
2. При пустой run API-связи убрать только commit lookup; прямой непустой
противоречащий run API-массив продолжает отклоняться. Общий SHA сам по себе
не даёт допуска. release-full сохраняет собственные event/path/candidate
проверки; single и feature режимы используют тот же verify_feature_runs.
3. Внешний pr-7123-fresh-recheck.json содержит PR7123/head751d52a...,
base7e60fba..., merge b74b3d9..., governance35139578748/attempt1 и полный
набор из трёх checks с digest. pr-7059-fresh-recheck.err содержит настоящий
отказ code receipt identity mismatch. Эти сохранённые результаты прочитаны,
новый live replay рецензент не запускал. Их давность не выдана за новую
приёмку; quickstart требует повторения после реализации.
4. Старое ожидание отказа только из-за commit_prs.append(9999) необходимо
заменить согласно новому контракту. Остальные отрицательные проверки
сохраняются. Mock успешного _github_pr_checks годится для проверки вызова,
а не для доказательства подлинности CI. Последнее требует общего suite и
настоящего read-only replay.
5. CHK008 повторно подтверждён: прочитана живая OPEN #7644 с каноническим
Spec tasks: T027, T028, T029 и отдельными критериями. У всех трёх задач есть
обратная ссылка (Issue #7644). Закрытая #7631 исключена из владения.
Quickstart/T028 прямо уточняют замену ошибочного commit-only ожидания и
сохранение остальных отказов. Самостоятельная приёмка F267 остаётся отдельной.

Изменены только собственный checklist и этот отчёт. Код, остальные списки,
спецификация, план, задачи, Git/GitHub, стенд и коммиты не изменялись.

## Повторное чтение списков

```json
{
  "numbering.md": {
    "checked": 6,
    "unchecked": 0
  },
  "pr-run-binding.md": {
    "checked": 8,
    "unchecked": 0
  },
  "requirements.md": {
    "checked": 13,
    "unchecked": 0
  },
  "three-digit-numbering.md": {
    "checked": 9,
    "unchecked": 0
  },
  "umbrella-ownership.md": {
    "checked": 7,
    "unchecked": 0
  }
}
```

## SHA-256 прочитанных источников

```json
{
  "AGENTS.md": "384c41c0b1674a3daf75d0e57646379198295c3f8452012c8101fc6332bec58b",
  ".specify/memory/constitution.md": "7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8",
  "docs/agent-guidance/spec-kit-flow.md": "5edf818b6ee27c7ee66d14edc003325ec7b16789eb1a195377cdeb901ae44887",
  "docs/agent-guidance/release-and-validation.md": "e3d24689a330634ec5ef87d829f8bcbf16bb7b81e0196b9d0baae4f49f27278d",
  "specs/259-audit-remediation/spec.md": "67f657a2a4e61640c64a9f597bf77d84ab4c623f1d72b56fa3a821c651cf08c6",
  "specs/259-audit-remediation/plan.md": "a47596213a67a9117149be041eae737d251a044c2364261536a28578243c26d8",
  "specs/259-audit-remediation/tasks.md": "61a1ffaeb9f62855fe447a9320d94941506e561095ab0b898308fa485dcdec54",
  "specs/259-audit-remediation/quickstart.md": "fd31832270ca3062d26aad50b02e8b96cbaa53a7de34bf428d1bab7029a9e5cb",
  "scripts/validate-issue-closeout.py": "0626370928c0f45a71bb3168194191bb449fd1af633d810bf8a6bea52a087b77",
  "scripts/validate-pr-checks.py": "3dadb1b84cfe45bbf4f06939981042ad2d1a0ff6aeb45928cf9e4a9ce0e3380e",
  "tests/governance/test_validator_safety.py": "97811576ef3888c99da556e33cd6e1ab31844f8d2e187e6e6843564ffa7f8a5a",
  "tests/governance/test_pr_checks.py": "e19800ce9b901ba81eaa837da9aaf109b620ab56073e460322d8d7699580f1e6",
  "specs/259-audit-remediation/checklists/numbering.md": "0700cdac78bd3040e1d7e0e9d7beed279c3c908bd4c8481c61d7d1d5bd641245",
  "specs/259-audit-remediation/checklists/pr-run-binding.md": "c530dede5b7aa6590e302b9e6d15df4274c5a44034557ac92f678e551b095a1d",
  "specs/259-audit-remediation/checklists/requirements.md": "cfa3307d4b18ba35f3dca4dbda42604971a1a85d9543937e6afb6d5440e946fb",
  "specs/259-audit-remediation/checklists/three-digit-numbering.md": "934f39d21ae3c97534ff9acc644f32802d0437667723c2e627ec06c0c7c0e52c",
  "specs/259-audit-remediation/checklists/umbrella-ownership.md": "6d6d0800f487967a5cf96994773f40833b8b853933ec165c2c6f49c4fedbc09d"
}
```
