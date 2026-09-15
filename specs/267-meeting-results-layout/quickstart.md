# Quickstart: F267

## Local prerequisites

From apps/server: uv sync --frozen --extra dev. From apps/server/tests/browser: npm ci.
Use the existing locked runtimes; browser automation on synthetic fixtures is allowed without installing an application. Do not launch another GRAF bundle.

## Focused checks

From apps/server:

```sh
.venv/bin/python -m pytest tests/unit/test_meeting_protocol.py tests/unit/test_meeting_protocol_rendering.py tests/unit/test_cabinet_web_shell.py tests/unit/test_outcome_prompts.py tests/unit/test_meeting_source_viewport_runtime.py tests/unit/test_user_time.py -q --tb=short
.venv/bin/ruff check src/twobrain_rec_server/outcomes src/twobrain_rec_server/cabinet src/twobrain_rec_server/cli/langfuse_prompts.py src/twobrain_rec_server/api/cabinet.py tests/unit/test_meeting_protocol_rendering.py tests/fixtures/meeting_results.py
node --check src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js
node --check tests/browser/meeting-results.test.cjs
node tests/browser/meeting-results.test.cjs
node tests/browser/protocol-source.test.cjs
node tests/browser/user-time.test.cjs
```

From the repository root, use the existing disposable Postgres runner, not the active Dev database:

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_meeting_protocol_generation.py -q --tb=short
bash apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_recording_share_public_link.py tests/unit/test_trusted_outcome_publication_boundary.py tests/unit/test_summary_candidate_revisions.py -q --tb=short
GRAF_NODE_MODULES="$PWD/apps/server/tests/browser/node_modules" bash apps/server/scripts/run_local_postgres_tests.sh --focused tests/contract/test_meeting_detail_reference_contract.py tests/contract/test_summary_template_ui_contract.py tests/contract/test_cabinet_static_assets_contract.py tests/contract/test_recording_workflow_accessibility.py tests/integration/test_cabinet_meeting_rename.py -q --tb=short
python3 scripts/validate-changelog-fragments.py
git diff --check
```

Run affected generation/config/replay tests named in tasks.md after publication marker changes. Tests must cover exact new/old descriptor and immutable pinned response recovery.
Mock sync_prompts/create_prompt for every built-in profile and custom: assert the new descriptor travels with the new text while the current model and supported parameters survive. This is a local synthetic check, not a Langfuse publication.

## Browser acceptance

The new browser script uses actual server-rendered synthetic detail/shared pages and local assets, without real data or provider calls. Check both themes, browser/embedded, 320/390/768/1024/1440 widths, 200% text. Assert one current title, semantic label, canonical local date, section order, closed topics/notes, single expansion, first source plus vertical overflow, keyboard/return navigation, unknown owner/due, long text and no page overflow.
Read generated screenshots in ignored output/playwright/f267. Read the synthetic full page as a user: subject is understandable, decisions differ from proposals, tasks are self-contained, topic outcome comes first. Keep screenshots out of git.

## Local app and live prompt

Read docs/agent-guidance/local-development.md and infra/dev/README.md before installed acceptance. At the start of validation, the active Dev belonged to F6793; this feature did not change it. Recheck current status before any later promotion. Promotion uses clean approved commit and build → promote → status → smoke; no alternate bundle or dirty-check bypass.
Changing the checked-in seed does not publish Langfuse. Evaluate exact new prompt/config on synthetic data through the configured approved gateway before separately authorized production promotion. Never repeat inference just to retry observation/storage.

## Final evidence

Report focused and browser results, screenshot/readability review and unresolved Dev/live-generation/PR gates separately. Implementation commit requires approval after validation. Do not claim release from local checks.

## Execution evidence — 2026-09-15–16

- Base HEAD: 5d0abfcd0e43f8e0640d665e0ac4ed913ebb411f. Results below apply to the uncommitted F267 working tree on that base, not to a committed candidate. Existing unrelated tooling/governance edits preserved; no implementation commit.
- Spec Kit analyze after seven tasks: 16 FR + 6 SC covered, 0 critical/high, no unmapped tasks. The installed prerequisite script lacks --require-spec; used --require-tasks --include-tasks plus an explicit nonempty spec check.
- Reviewer: requirements 16/16, UX 11/11, infra 5/5. Issue canon ensure/validate passed, 300 open Spec Kit issues checked; only F267 issues created.
- Umbrella #7015; task owners T001→#7020, T002→#7021, T003→#7022, T004→#7023, T005→#7024, T006→#7025, T007→#7026. All remain open pending merged/exact-SHA acceptance.
- Final disjoint Python suites: **411 passed**. Protocol/render/shell/prompt configuration: 157; generation/persistence/replay: 31; shared links/publication boundaries/candidate revisions: 48; UI contracts/accessibility/rename: 160; source viewport/user time: 15. The initial 38-test baseline is not counted again. Disposable test containers were removed by the runner; the existing Dev database was not used.
- Chromium and WebKit: **156 layout configurations passed**, plus disclosure/source/keyboard interactions. The main matrix covers 320/390/768/1024/1440 CSS px, light/dark, browser/embedded/shared and actual 200% text enlargement. Chromium additionally checks long/empty/legacy/category-only/read-only/stale-revision variants at 320 px with doubled text.
- Browser assertions passed for no page overflow, contrast ≥4.5, text line-height ≥1.45, control targets ≥24 px, visible unobscured focus, initial closure, vertical source list, exact transcript segment without audio, and return focus. Selecting a source inside a topic does not close that topic. Shared pages expose no unavailable source controls.
- Existing protocol-source and user-time browser scripts passed; the format picker passed through its existing contract wrapper. Final focused Ruff, JavaScript syntax, changelog-fragment validator and `git diff --check` passed. Two existing pytest warnings remain (plugin import rewrite and Starlette/httpx deprecation).

### Visual and reading review

- Read actual server-rendered synthetic content and inspected desktop/mobile, expanded-topic, shared-page and dark embedded task screenshots under ignored `output/playwright/f267/`. No private meeting content or third-party assets were used.
- Fixed an oversized sticky header on noneditable detail by extending the existing header observer; it yields space when it would cover the document. Long historical headings now wrap at 200% text.
- Fixed narrow task columns splitting names/deadlines into fragments. The existing semantic table stacks each task, owner and due date through a CSS container query; no duplicate data or second component. Shared paragraphs use the same calm spacing as full-protocol detail.
- Reading result: the subject adds meaning to the title; takeaways and decisions are available before topic details; tasks name the action with owner/deadline or honest unknown states. A proposal remains a proposal, a deferred choice stays explicit, and one topic expansion reveals its outcome first. No serious readability/layout defects remain in the tested matrix.
- Useful local screenshots: `chromium-light-browser-1440.png`, `chromium-light-browser-390.png`, `chromium-dark-browser-topic.png`, `chromium-light-shared-tasks.png`, `webkit-dark-embedded-tasks.png`.

### Final review and convergence

- `code-reviewer` and `web-design-guidelines`: no unresolved findings in the F267 scope after the fixes above. Verified every shared HTML caller, safe text escaping, source/revision guards, original prompt-core integrity, pinned old/new contract recovery and unchanged complete export.
- `speckit-converge`: **converged**, 16 FR + 6 SC + 15 acceptance scenarios, seven design decisions and four applicable constitution principles (III, IV, VI, VII) checked. Principles I, II and V are outside the changed runtime scope. Findings: missing 0, partial 0, contradicts 0, unrequested 0; critical/high/medium/low all 0.
- The convergence phase left `tasks.md` byte-for-byte unchanged (SHA-256 `80e21d13f811c8cba1ea3fe52154848b1559832a7033ab1047a94a23f51886b8`). T006/T007 completion markers were updated only afterward as implementation bookkeeping; reviewer-owned checklist markers were not changed. No enabled before/after converge or implement hooks require execution.
- Local implementation and validation are complete; tracker acceptance remains pending. No issues are closable from these local results alone: #7015 and #7020–#7026 await merged/exact-SHA evidence. No commit, push, PR, production deployment or Dev promotion was performed.
- Remaining separate gates: user-approved implementation commit preserving unrelated work; required `governance-fast`, `macos-pr`, `pr-metadata` on the exact PR SHA; installed acceptance through the single `/Applications/GRAF Dev.app` and its harness. Direct WebKit tests do not prove installed-app behavior.
- The source prompt/config and old/new persistence behavior were tested locally, but live model output was not evaluated and Langfuse labels were not changed. Deploy generation-side provenance classification before separately authorized activation of the evaluated new prompt/config. Historical meetings are not regenerated automatically.

## Уточнение: источник в строке мысли — 2026-09-16

- Пользователь уточнил FR-009/SC-003: источник продолжает текущую мысль без принудительного переноса, следующая мысль начинается отдельным абзацем. Работа остаётся в текущем F267 (`high-risk-product`), T005–T007; новых задач и сущностей нет.
- Причина устранена в общем `_render_outcome_item` и двух существующих CSS-правилах: текст строчный, группа источников `inline-flex`, дополнительные сведения идут после источника. Каждый тезис сохраняет собственный блочный контейнер и отступ. Естественный перенос при нехватке ширины разрешён; JavaScript, права, источники и экспорт не менялись.
- До исправления дополненные проверки воспроизвели дефект: два unit-сценария порядка источника/метаданных и браузерная проверка положения источника относительно последней строки текста. После исправления 157 focused tests прошли: protocol/render/export, cabinet shell, source viewport и user time. Результат 411 выше относится к полной предыдущей проверке; неизменённые generation/DB suites повторно не запускались.
- Повторная полная браузерная матрица: 156 конфигураций Chromium/WebKit плюс взаимодействия PASS. Новая проверка подтверждает источник на последней строке текста при достаточной ширине и отдельный следующий абзац. Проверены прежние размеры, темы, 200% text и крайние состояния; `protocol-source.test.cjs`, Ruff, JS syntax и `git diff --check` PASS.
- Обновлённые снимки широкого/узкого экрана и раскрытой темы в тёмном оформлении прочитаны визуально; принудительного переноса, горизонтального переполнения и потери разделения мыслей нет. Источник может естественно занять следующую строку, если оставшегося места недостаточно.
- Повторный analyze: 22 FR/SC, семь задач, покрытие 100%, замечаний нет. Converge изменённых требований и T005–T007: `converged`, новых работ нет; во время проверки `tasks.md` оставался неизменным (SHA-256 `0ad595050787fe07d42c43485e6156fe657e4fffc26901f6b77958f1b333f85b`), отметки выполнения восстановлены после неё. Reviewer-owned checklists не менялись.
- Коммит, PR, Dev promotion и live Langfuse не выполнялись. GitHub issues остаются открытыми до ранее указанных merged/exact-SHA gates.

## Подготовка PR и включения в релиз — 2026-09-16

- Пользователь разрешил коммит, push и подготовку к релизу. Публикация релиза, merge, production и переключение Langfuse остаются отдельными действиями.
- F267 перенесена на актуальную базу `bb09c4ee2abff20dfe0e25b4bea009bf7c8878d4`; семь новых коммитов master, включая F265, сохранены. Код объединился без конфликтов. Посторонние правки не включены в feature commit; исходное состояние сохранено в локальной Git-ссылке `refs/backups/f267-6389f6800-before-rebase`. Две служебные даты Spec Kit оставлены как локальные изменения.
- После переноса повторно прошли 172 protocol/render/shell/prompt/viewport/time теста, 156 вариантов вёрстки Chromium/WebKit, существующие source/time проверки и `local-recording-handoff.test.cjs` из F265. Ruff, `validate-agent-context.py`, `check_spec_kit_governance.py`, changelog validator и `speckit-bootstrap . --doctor --frozen` PASS.
- Проверка подготовки выявила недостающую декларацию Legacy Impact в spec; она добавлена без изменения кода и проверяется штатным `check-development-process.py`.
- Итоговые SHA, ссылка PR и результаты обязательных GitHub checks фиксируются в описании PR после коммита. Старые результаты выше остаются историческими и не заменяют проверки итогового SHA.
- До merge требуется отдельная приёмка установленного `/Applications/GRAF Dev.app`; прямые Chromium/WebKit проверки её не заменяют. Для активации новой инструкции Langfuse дополнительно нужны оценка точной версии на синтетических данных и отдельное разрешение. До активации новая вёрстка безопасно показывает историческое «Тип встречи».
- Фрагмент `changes/unreleased/F267.yaml` готов для сборки release operator. Подготовленный в master выпуск `v2026.09.16.1` не изменялся; последним опубликованным стабильным релизом на момент проверки был `v2026.09.13.3`. Номер и состав следующего выпуска определяются после согласованного merge, затем выполняется единый frozen-candidate `release-full`.
