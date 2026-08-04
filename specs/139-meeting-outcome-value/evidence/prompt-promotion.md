# Prompt promotion receipt

Дата: `2026-08-04`
Lane: approved production prompt gate; metadata-only evidence.
Статус: `pass` — exact promotion, readback, private synthetic e2e и rollback
rehearsal завершены. До deploy совместимого server SHA outcome labels намеренно
возвращены на `v3`; gated control prompts остаются в production.

## Approval and transition

- Явное operator approval получено от пользователя task 4 августа 2026 года.
- Protected-label/sole-credential readiness: `pass`; prompt count: `14/14`.
- Promotion run id: `514f9d5e-18a1-45ad-beca-432fb642bf52`.
- Metadata-only promotion trace id:
  `e5801a2f125d6b60cdf2305f8fbc7f46`; observations: `1`.
- Every move used exact expected-source verification, cache clear and independent
  `production` readback. Content printed or committed: `false`.

Новая response schema требует хотя бы один source ref. Исторический outcome
`v3` был создан до этого invariant и не является валидным rollback target для
нового runtime. Поэтому до label move были созданы unlabelled runtime-compatible
rollback versions: текст `v3` плюс строгая schema текущего candidate. Это
сохраняет поведение отката и не ослабляет trust boundary.

## Outcome target and rollback matrix

Каждый target `v5` был назначен `production`, перечитан по label и проверен по
exact canonical hash. После e2e он возвращён на `v3`, чтобы ещё работающий
старый runtime продолжал принимать свой schema contract. Финальный повторный
move `v3 → v5` выполняется только после deploy совместимого SHA.

| Prompt | Verified target hash | Prepared rollback |
|---|---|---|
| `graf/meeting-outcome/auto` | `v5` `c3f0e9de6f17e4e4d07c7c5b4e15c3585c3bd2bd75344e6f53ce1ea048e0c2ce` | `v6` `4d8ce870196a3d0e2a6e8b3cc69738ed6bb64bf624ec27a39c3cfd87e7912ee7` |
| `graf/meeting-outcome/outline` | `v5` `a02f6a8352b82d8bff34810c4681e8db71d560d99b951df59786565d0510b9e7` | `v6` `00b30a00cbcfd6e09a5600a2fc63628143ac9c0052ef2f43bb3ce2648c7b6f35` |
| `graf/meeting-outcome/meeting-minutes` | `v5` `e4a16292a15c6988515ff66a3d9d9ab5a7283f8d6a253fc235c67d8e60d34f55` | `v6` `c63b65436bd8fecf8983ed78e438fb8c591fb58550120088c99f292a516bcc67` |
| `graf/meeting-outcome/project-sync` | `v5` `9bd59e99ebac669fe06f7cca6b7fe70b1b11aba9fbf396952b0225fa916f2e5c` | `v6` `83608c73dd18c73794ac7b462b58744a8cb5400eff027c81e0deae9796559f42` |
| `graf/meeting-outcome/weekly-team-meeting` | `v5` `00cd1ecf073beb3e0dd18be51cc802bb99c05015a70874c7839d0933a4a3701f` | `v6` `01c10b652c55a1a581ab16d82c6597300267011ca97115699c7b0e7745a3a9fd` |
| `graf/meeting-outcome/one-to-one` | `v5` `d71acfd4877428d3bd882691bb8799eccea24efd2d90c4c47669f0eb9d8a642c` | `v6` `8df462458e38b629fcae2da8dafe04472ef81b438283fb8e9884e2665bdeea85` |
| `graf/meeting-outcome/client-status-update` | `v5` `32f5c330cbaf8ec7b39ceb2de62670db662d28479e7d835bf01bf9878b172f04` | `v6` `eac2654efe411f4d305969f7ce7053d532b0def905c1d8300237f35dd5ef077b` |
| `graf/meeting-outcome/interview` | `v5` `9ba22014c0da549120887b692a997a8b7c05bca77dfd669b565736c43d9b6a82` | `v6` `1bcb6f75730c369fbf9bf502d669cbf8545dd599599f9b9564ed2c283a2a5092` |
| `graf/meeting-outcome/sales-discovery` | `v5` `5440ed16636879512e44639ee7055673671410f843a59408bbf24331ddce78ea` | `v6` `50cb99419e419f8116ed5150be249ed20705daff66a75bc9fc35dd7c6599624a` |
| `graf/meeting-outcome/custom` | `v5` `3236d6e8cd2c86c16a4eb5655bbc2e7767a5a3f1af33951338ac6d46759c8ce8` | `v6` `8d488b3d25014ccb16f9efc72bb02b7b1cea51086528204933fb294e8d077ad3` |

Compatibility rollback run id:
`36580e34-623c-47ed-94bc-6c4f862642f5`; trace id:
`9b6e42837df452e0f7994f1475f18c3f`. Independent final readback: `10/10`
outcomes point to exact historical `v3` hashes.

## Gated control production versions

Control promotion creates a new immutable version containing the passing prompt
plus aggregate gate and exact evidence hash.

| Prompt | Candidate | Production / hash | Evidence hash | Rollback |
|---|---:|---|---|---:|
| `graf/prompt-optimization/reflection` | `v7` | `v8` `c8d26640876ba89c68d61822ec1e00d3ac7fe6bcb11e82dd091a345d1904dc96` | `fb707fc017187cc840c2c4c19391afc23c78e1b3cf8db4df4ebde1b50eb13473` | `v5` |
| `graf/evaluation/meeting-outcome-faithfulness` | `v6` | `v7` `2cca71f382bdbedfe5c4e68952b43653b91f105c6beba8933e1e8bf8e1f2ba0b` | `0d39a6c63ed7f17bd73bf2d9d74673ce7061354a5ee8986f5b5aff949e7f5199` | `v4` |
| `graf/evaluation/meeting-outcome-action-items` | `v7` | `v8` `1d92850bdde69c71b7a8fbb68ac63c55c9512b5cef231a9d21d37f1bb082b867` | `23031d2cda49a0d7fd7e16b0539521fdc64cd91e263f7bf357e944c718a0c1e9` | `v4` |
| `graf/evaluation/meeting-outcome-completeness` | `v6` | `v7` `2b71499f4b8c79f811611fd9e6b0632d1502bf1a5f3dc73dd7182acac9655efa` | `2f1b1ee6a24a664afe792df3529622b40e14bc2ea924f53392e985b93ae91a44` | `v4` |

Judge calibration: `10/10`, agreement/threshold `1.00`, invalid output `0` for
each judge. Reflection parser/variables/anti-copy/bounded-cost gate: `pass`.

## Private synthetic end-to-end

- Passing run id: `b279e019-af74-4db9-9632-70628307ee98`.
- Langfuse trace id: `07227e76c4330da590efda865e37bbc8`.
- Observations: `6` = `5` complete model calls plus terminal receipt.
- Production readback before egress: `14/14`.
- Outcome prompt: exact `graf/meeting-outcome/auto@v5`, hash
  `c3f0e9de6f17e4e4d07c7c5b4e15c3585c3bd2bd75344e6f53ce1ea048e0c2ce`.
- Result contract: one decision, one action, exact reference validation,
  explicit owner/due validation — `pass`.
- Faithfulness `v7`, action-items `v8`, completeness `v7`: score `1.00`, verdict
  `pass` for all three.
- Reflection `v8`: complete-prompt parser/preservation smoke `pass`.
- Frozen adversarial injection gate remains `1.00`; no adversarial content was
  mixed into the final operational smoke.
- Content printed or committed: `false`.

Один ранний diagnostic smoke смешивал operational и adversarial цели и был
остановлен первым judge gate. Trace
`d52b3b2735383e42d5016a1c5ddb5f08` содержит одну retained task observation;
run id `9efbb8b8-ccb7-4074-9a69-87316e5fdaaa`. Operator harness был исправлен:
final smoke публикует каждую generation до gate check и не заменяет frozen
held-out claim.

## Final pre-deploy state

- Runtime-safe readback: `pass`, prompt count `14/14`.
- Outcome production: exact `v3` until compatible server deploy.
- Control production: reflection `v8`, faithfulness `v7`, action-items `v8`,
  completeness `v7`.
- After merged SHA deploy, T049 повторно назначает exact outcome `v5`, проверяет
  prepared `v6` rollback и только затем запускает production smoke.
