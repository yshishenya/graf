# T098 — проверка требований точного набора PR

Reviewer-owned: implementation не отмечает пункты.

- [x] CHK001 Разные PR с общей checked base требуют отдельных успешных proof; каждый пропуск и ошибка раннего PR блокируют train.
- [x] CHK002 Настоящий linear rebase одного PR с несколькими commits имеет один terminal merge owner и один proof.
- [x] CHK003 Missing terminal, ambiguous intermediate owner и changing merge identity дают отказ; старые negatives/parallel two-prs сохранены.
- [x] CHK004 Минимальная правка не меняет checked_base, proof identity/свежесть, concurrency, protection, Full, backup или CD.
- [x] CHK005 Новый train содержит весь фактический range, включая PR исправления; live verifier, exact required checks и единственный frozen Full обязательны.

## Независимое requirements review, 2026-10-06

Reviewer: отдельный агент `release_identity_review`. PASS — 5 checked,
0 unchecked. Это проверка полноты и согласованности требований до кода;
галочки не означают успешные новые tests, GitHub checks, Full или CD.

- CHK001: `spec.md`, уточнение T098, требует собственный успешный proof
  каждого точного PR и отказ при неполном included_prs; `plan.md`, T098,
  шаги 2–3, явно требует оба PR7/8, пропуск каждого и ошибку раннего PR.
  Реальный `git log --first-parent 29264c6..b8d56ea` содержит три разных
  merge commits 9b8a7a5 / 98bf111 / b8d56ea. Текущий `verify_source`
  ошибочно считает covered весь checked-base..merge диапазон.
- CHK002: уточнение T098 задаёт несколько original/rebased commits одного
  PR, единственного terminal merge owner и один proof; шаг 2 плана требует
  настоящий временный Git. Старый test case `rebase` реально возвращает
  владельцев 7 и 8, поэтому его переименование и ожидание [7,8] обоснованы.
- CHK003: все три отказа названы в уточнении, плане и задаче T098;
  отдельные прежние отрицательные случаи и parallel two-prs сохраняются.
  Текущий код содержит deferred-owner, unique-owner и merge-identity gates;
  требования не разрешают их обхода.
- CHK004: план ограничивает правку набором проверенных номеров PR и
  комментарием; оставляет derivation, deferred owners, verify, pool и proof
  gates. Spec исключает смену checked_base/protection/proofs. Это согласуется
  с конституцией 7.1.0 и `release-and-validation.md`: exact head/base,
  свежие run/attempt artifacts, обязательные Full/backup/dry-run/CD.
- CHK005: уточнение и шаг 5 плана требуют новый train с PR исправления,
  exact SHA/base required checks и live verifier, затем единственный frozen
  Full. `quickstart.md`, T098, отдельно различает synthetic API tests и
  production evidence. Порядок соответствует release guidance.

Блокеров требований нет. Analyze, issue sync, локальные регрессии,
implementation review и реальные release gates остаются отдельными
обязательными шагами. Чеклист перечитан после изменения: 5/0.

## Независимое implementation review, 2026-10-06

Reviewer: тот же отдельный агент `release_identity_review`. Итог PASS:
HIGH 0, MEDIUM 0. Requirements checklist перечитан: 5 checked / 0 unchecked.

Проверен окончательный diff `scripts/validate-pr-checks.py` и
`tests/governance/test_pr_checks.py`. Production change ограничен набором
точных PR numbers вместо broad checked-base..merge coverage и поясняющим
комментарием. Сохраняются published-base derivation, unique/deferred owners,
merge identity, исходный `verify`, bounded pool, порядок результатов и exact
included_prs. Ошибка proof отдельного раннего PR теперь достигает вызывающего
кода; proof другого PR не может её скрыть.

Старый ошибочный `rebase` переименован в `overlapping-checked-ranges` и
ожидает [7,8]. Сохранены mixed-prs negative, все прежние отрицательные cases
и barrier/max_active проверка настоящей параллельности. Новые cases проверяют
пропуск каждого PR, missing/unsuccessful proof раннего PR, реальный Git rebase,
missing terminal owner, ambiguous intermediate owner и changing merge identity.

Во время review найден и исправлен один MEDIUM в новом rebase fixture:
успешный receipt PR8 первоначально имел неверную checked base. Окончательный
fixture создаёт три исходных commits от `first`, настоящим force-rebase
пересоздаёт три Git commits с другим committer date и той же base `first`;
проверяет непересекающиеся SHA, одинаковые final trees и first-parent range.
Receipt PR7 имеет base `base`, PR8 — `first` и original head. Проверяется один
proof PR8 для трёх rebased commits. Это сохранение корректного прежнего
поведения; старый log с третьим FAIL на ранней версии fixture не считается
регрессией настоящего успешного rebase.

Доказательства: `../ci-evidence/release-pr-identity-before.log` подтверждает
исходный отказ overlapping ranges и ложный допуск omitted earlier PR;
`release-pr-identity-proof-before.log` подтверждает скрытые missing/unsuccessful
proof причины. `release-pr-identity-focused.log` содержит 135 PASS для PR
validator и отдельно ошибку среды consumer запуска; исправленный запуск
`release-pr-identity-consumers.log` содержит 28 PASS. Reviewer независимо
запустил ownership/merged-history выборку: 41 PASS, 94 deselected; затем
перечитав corrected fixture запустил его отдельно: 4 PASS, 131 deselected.
Окончательный `release-pr-identity-final.log` после исправления fixture:
135 PASS / 24,18 с.
Это локальные синтетические tests с настоящим временным Git; live required
checks, полный train, frozen Full и CD ими не подтверждаются.
