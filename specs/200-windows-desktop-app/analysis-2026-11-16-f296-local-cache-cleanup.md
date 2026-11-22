# F296 в F200: scoped speckit-analyze Main, 16.11.2026

**PASS — consistency до T128, C0/H0/M0/L0.** Lane high-risk-product.
Рассмотрены R01–R08, Phase29 T128–T133, F296 plan/quickstart, весь новый
Windows cache contract и независимый review R2/checklist12/12. Общие
конституционные storage/owner/deletion truth, safe diagnostics и visible Stop
сохраняются; поблажек privacy/custody нет. Уточнения H1/M1 приняты Main,
задачи приняты после reviewer gate через существующий setup-tasks.

Противоречий/дублирования/непокрытых требований и orphan tasks не найдено.
Missing/null/malformed/mismatched finalized local ID → keep/0effects обязательно,
отклонение от optional Mac guard legacy/unknown названо явно.
UUID server и local ID раздельны. Full valid proof сохраняет parity.

| Требование | Задачи | Проверка |
|---|---|---|
| R01 | T129,T130 | WAV-only, retained bytes/queue identity неизменны |
| R02 | T128 | fresh read-only GET; positive/negative/time/namespace boundaries |
| R03 | T129,T130 | durable pending ACK, crash cuts/absence/completed, BOTH slots |
| R04 | T129,T130,T133 | typed partial playback/full upload refusal/cold/rollback |
| R05 | T131,T133 | native confirmation/cancel0effects/capabilities/UIA/Stop |
| R06 | T132,T133 | same primitive/settings/single-flight/pressure/bounds |
| R07 | T128–T132 | protected IO, account fences, memory/admission unchanged |
| R08 | T133 | actual native/installed evidence, regressions и отдельный release |

8 требований/6 задач/100% покрытие; ambiguity0, duplication0, C/H/M/L0.
Порядок T128→T129→T130→T131→T132→T133 без [P] согласован с shared ownership.
Граница допуска разделена: общие requirements/checklist/analyze/issues позволяют
только T128 GET/parser/eligibility и неразрушающие тесты. T129 сначала фиксирует
exact wire/version/layout/limits/BOTH slots/old-reader refusal/rollback и проходит
независимое wire/codec/consumer review до codec/readers/writers. Неизвестный
пока exact wire — явно запланированный engineering gate T129, не ambiguity
для неразрушающего T128. T130 зависит от T129; UI/auto не получают отдельного
разрешения на delete. Frozen partial artifacts нужны соответствующей приёмке,
не старта T128: круговой gate устранён.

Анализ выполнен read-only; сохранение этого отчёта — последующая фиксация этапа.
Installed prerequisite script использован --json --paths-only, наличие
spec/plan/tasks и 6уникальных task IDs проверено отдельно. Active pointer F200
сохранён. Before/after analyze hooks disabled; reviewer marks Main не меняет.
До source остаётся canonical task issue sync; после реализации нужны source
review/converge/native/installed/release gates по назначению.
Это не реализация/нативная приёмка/разрешение удаления личных записей.

## Inputs SHA-256

- `spec.md`: `01a8d070bd5166525cfe438bc6a45e8ddaf24e92126fff4d1475263db2357d5a`.
- `plan.md`: `5431a4febf82f0d632d4ad8a31672fb09ae171ef726e10f7048ffb6460cd9119`.
- `tasks.md`: `d0e6343d73a462c3707a88f04ba79e4f88b5ea1c827f4c28bc18d73424ea8c2f`.
- `quickstart.md`: `e0ba800d4338fd397650a9b8d20165b32b92e501aaef168bc18357d7af490687`.
- `contracts/windows-local-cache-cleanup.md`: `f25c00e8e29e84f472f07b0145bda6f5b8a454ea61a01101848119dc6829cbed`.
- `checklists/f296-local-cache-cleanup.md`: `fd6589749f4da0fd96c35266516c44efe90c2bee3fee902b1d85e4dfff4ac2be`.

Issue sync Main: T128=#8107,T129=#8108,T130=#8109,T131=#8110,T132=#8111,T133=#8112.
Dedup проверил117 all-state feature200 и6 отдельных task searches; владельцев
до создания не было. Actual canonical ensure/validate PASS300; GitHub API
ошибка первого validate сохранена, успешный повтор исходного script выполнен
с GODEBUG=http2client=0, без ослабления validator.
Повторная scoped consistency после добавления issue-links: C0/H0/M0/L0,
8 требований/6 задач/100% coverage и зависимости неизменны. Current tasks
SHA-256 `59e551f1c22c3727b0f82e2ac7fa480edf0cd478c4d712d45812133147df0cf3`. Только T128 read-only source допускается; T129 gate остаётся.
