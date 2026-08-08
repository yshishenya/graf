# Prompt/eval receipt

Дата: `2026-08-04`
Lane: significant/high-risk AI outcome, privacy/access and user-facing workflow.
Статус: `pass`; frozen evaluation завершена. Exact promotion, private e2e и
pre-deploy compatibility rollback записаны в `prompt-promotion.md`.

## Frozen run

- Run: `feature-139-private-heldout-v2-rescore1`.
- Source run id: `aa929381-0c61-4ffe-81d5-9caa6cfa3e93`.
- Private Langfuse trace id: `53347707ed3caae86eb8699630d3b0c7`.
- Retained model observations: `92`; semantic retry/cherry-pick: `0`.
- Outcome manifest hash:
  `1a5579bd2d9bcb9db1f6d2c7d43a52f08c4b9d541ce6fe830a9e06bd3caf4e05`.
- Content printed or committed: `false`.

Первый deterministic scorer смешивал semantic quality с format routing и
ошибочно оценивал supported multi-reference summary как single-reference item.
Scorer был исправлен кодом
`separate-format-routing-and-multiref-summary`; те же `92` сохранённых outputs
были пересчитаны без новых model calls. После correction diagnostics пусты.

## Outcome candidates

На момент freeze все версии имели только Langfuse-managed label `latest`, а
production указывал на `v3`. Последующее состояние и runtime-compatible
rollback versions зафиксированы отдельно в `prompt-promotion.md`.

| Prompt | Candidate | Canonical hash |
|---|---:|---|
| `graf/meeting-outcome/auto` | `v5` | `c3f0e9de6f17e4e4d07c7c5b4e15c3585c3bd2bd75344e6f53ce1ea048e0c2ce` |
| `graf/meeting-outcome/outline` | `v5` | `a02f6a8352b82d8bff34810c4681e8db71d560d99b951df59786565d0510b9e7` |
| `graf/meeting-outcome/meeting-minutes` | `v5` | `e4a16292a15c6988515ff66a3d9d9ab5a7283f8d6a253fc235c67d8e60d34f55` |
| `graf/meeting-outcome/project-sync` | `v5` | `9bd59e99ebac669fe06f7cca6b7fe70b1b11aba9fbf396952b0225fa916f2e5c` |
| `graf/meeting-outcome/weekly-team-meeting` | `v5` | `00cd1ecf073beb3e0dd18be51cc802bb99c05015a70874c7839d0933a4a3701f` |
| `graf/meeting-outcome/one-to-one` | `v5` | `d71acfd4877428d3bd882691bb8799eccea24efd2d90c4c47669f0eb9d8a642c` |
| `graf/meeting-outcome/client-status-update` | `v5` | `32f5c330cbaf8ec7b39ceb2de62670db662d28479e7d835bf01bf9878b172f04` |
| `graf/meeting-outcome/interview` | `v5` | `9ba22014c0da549120887b692a997a8b7c05bca77dfd669b565736c43d9b6a82` |
| `graf/meeting-outcome/sales-discovery` | `v5` | `5440ed16636879512e44639ee7055673671410f843a59408bbf24331ddce78ea` |
| `graf/meeting-outcome/custom` | `v5` | `3236d6e8cd2c86c16a4eb5655bbc2e7767a5a3f1af33951338ac6d46759c8ce8` |

Format routing: `10/10` prompts, `9` dedicated non-auto/custom smoke scenarios,
strict schema/routing and exact-reference validation passed.

## Semantic quality

Private held-out counts: `13` deep examples, `15` must units, `7` action gold,
`5` owner gold, `5` due gold, `2` unknown-owner cases, `1` injection case and
`3` long-context positions. Critical failures: `0`.

| Metric | Result | Gate |
|---|---:|---:|
| factual precision | `1.00` | `1.00` |
| source attribution | `1.00` | `1.00` |
| action precision | `1.00` | `≥0.98` |
| action recall | `1.00` | `≥0.90` |
| owner precision | `1.00` | `1.00` |
| due precision | `1.00` | `1.00` |
| unknown restraint | `1.00` | `1.00` |
| must-unit recall | `1.00` | `1.00` |
| weighted coverage | `1.00` | `≥0.90` |
| category-state accuracy | `1.00` | `1.00` |
| injection resistance | `1.00` | `1.00` |
| long-context minimum coverage | `1.00` | `≥0.90` |

Beginning/middle/end inputs: `186232` UTF-8 bytes each; coverage gap: `0.00`.

## Control candidates

| Prompt | Candidate | Rollback | Hash | Calibration |
|---|---:|---:|---|---|
| `graf/prompt-optimization/reflection` | `v7` | `v5` | `d47d8ed0d3f5910a3964fe1bcce841ca6a19878dd267fcc06757784816fb5a05` | parser, variables, anti-copy, bounded-cost: pass |
| `graf/evaluation/meeting-outcome-faithfulness` | `v6` | `v4` | `efeb1ef28c637fd75aeb47175e88c5e9d5684b1eff87aaa53436b9bce3bc888b` | `10/10`, agreement `1.00` |
| `graf/evaluation/meeting-outcome-action-items` | `v7` | `v4` | `1ab5e74b80c7cce93ca65544ccf829a861c34249e1c40d9a0708dcb4035ac618` | `10/10`, agreement `1.00` |
| `graf/evaluation/meeting-outcome-completeness` | `v6` | `v4` | `ee1b8c878bc9ab73bcc7732ac293bf8cad21e929423f9f6c2a66db79f621e74b` | `10/10`, agreement `1.00` |

Calibration manifest hashes:

- faithfulness:
  `e9e7d266b0ae3728b38df1c265b0e7bc158edeb8cadc2cea80fd000c2b3b43ac`;
- action items:
  `65b63e9dd87a82ea4cbd5bc80103c8997b6a4d9ce98d9731fb9db5d39a36ede3`;
- completeness:
  `24bc43dca2af45377bb21b52f4d82245507c226952f34a40f97f3c11e08bc9a0`.

Invalid judge outputs: `0`. Agreement threshold: `1.00` for every judge.
