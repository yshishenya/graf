# F273/T106 — совместимость учебных предпосылок

Основа e4762f64ba7bab08e2a06f51a15bf370d30d3295. Lane active Spec Kit slice.

До кода выполнен scoped analyze: public scope, валидный register, независимые
restore/network guards и честные границы принятия — 4/4 покрыты существующей
T106/#7696; CRITICAL/HIGH/MEDIUM 0, unmapped 0. Конституция II/III/IV/VI
не меняется. Новых требований/задач/данных/транспортов нет. Before-code review
проверил все 5 пунктов существующего checklist: 5 отмечены/0 открыты, P1/P2/HIGH0.
Связь существующего T106/#7696 сохранена; новых issue не создаётся. Прежнее подтверждение
синхронизации T106/#7696 прочитано в .dev/public-server-gate/issue-comment.md;
после восстановления API перед PR повторно сверить текущую issue связь.

Три исходных отказа воспроизведены на неизменном source: 3 failed/2.22s.
Те же три сценария с единственным внешним временным valid version1 basis
на неизменном source дали 3 passed/1.08s. Это причинное доказательство
отсутствующей учебной предпосылки, не дефект рабочего fail-closed решения.
Журналы RED/cause находятся в release clone .dev/release/public-smoke-*-20261101.log.

Минимальная правка: test_093 явно запрашивает existing public_basis_register;
smoke создаёт свой прежний legal_basis_state_file раньше и временно задаёт env
только вокруг настоящего public builder через существующий patch.dict.
Дальнейший live_environment использует тот же файл. Рабочий код, blocker/reader,
consent/catalog scope, assertions и audit hook не менялись.

GREEN профиль: весь page-scope, оба provider-smoke контракта, public unit,
legal-basis lifecycle и provider-delivery gate — 53 passed/0 skipped/2.04s.
SHA256 журнала .dev/public-smoke-basis/green.log:
b3c948112a62a7d5285071869b028f3e8b6e842d995e97d4d2f56748c2e22452.

Public contract профиль с настоящим consent modal и PostgreSQL: 36 passed/
0 skipped/16.85s; runner duration21s, isolated_container_removed. Журнал
.dev/public-smoke-basis/public-contracts-final.log SHA256:
822c49659e28e23be043685db9693711badc6d7b54eee6ac9e26dbd4153a9039.
Первые две попытки этого runner содержали неверные пути, EXIT4/no tests
collected/container_not_started; они сохранены отдельно и не считаются PASS.

Ruff затронутого Python test, bash -n, development-process, fragment validator,
Spec Kit governance и git diff --check PASS. Независимое after-code review и
сверка выполнения узкого плана PASS: checklist5/0, P1/P2/HIGH0;
новых незакрытых работ в этом срезе не найдено. GitHub checks, merge, Full, CD, рабочее включение,
T0 и коммерческий рост не приняты этим локальным результатом. Общие T106/T118
остаются открытыми; учебная подстановка restore_consistent ограничена прежним
тестовым процессом, настоящий restore до/после транспорта закрыт.
