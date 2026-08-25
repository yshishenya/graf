# Closeout

Дата: 2026-08-21

Ветка: `181-meeting-summary-experience`

Base SHA: `c72e190d2de14c054fe6ebc04733021240d7f03e`

Risk lane: high-risk Spec Kit — AI, private meeting data, accepted-result integrity и core UX.

## Evidence

- Focused PostgreSQL suite after master refresh: 91 passed, 2 warnings, exit 0.
- Browser/desktop/mobile/200% matrix: pass по зафиксированным rows в `ui-matrix.md`.
- Codex Security diff scan `903d53a1-ea45-46e4-81f0-6bc1ccb62525`: complete coverage, 43/43 review receipts; один Medium и один Low finding до remediation.
- Current lifecycle: automatic result публикуется в target slot после trusted
  validation; `.playwright-cli/` удалён из worktree и игнорируется.
- `infra/scripts/ci-local.sh --fast` after master refresh: pass — 1232 passed, 2 warnings, server lint pass, Python compile pass, exit 0.
- Final Ponytail review: выполнен; сокращены duplicate history recovery UI, constant candidate-state parametrization и duplicate synthetic prompt compilation. Явные safety arguments и accessibility assertions сохранены намеренно.
- Post-remediation security rerun `685c8960-6d7a-4aec-8c9b-a48ec272eca2`: no candidates в проверенном final state, но scan помечен partial из-за изменения worktree во время review; immutable rerun выполняется после полного freeze diff.
- Tracker reconciliation: комментарий к `#5517` — https://github.com/yshishenya/crisp/issues/5517#issuecomment-5372156880; issue оставлен открытым.
- Повторная проверка 2026-08-24 на commit `774727f0`: focused PostgreSQL suite — `90 passed`, 2 предупреждения, exit 0; `infra/scripts/ci-local.sh --fast` — `1132 passed`, server lint и Python compile pass, exit 0.
- Commit `774727f0` опубликован в `origin/181-meeting-summary-experience`; production deploy не выполнялся.
- Ветка сверена с актуальным `origin/master` (`a12c0b55`): merge-конфликты разрешены, текущий merge оставлен staged до отдельного разрешения на commit/push; исходная точка сохранена в `codex/181-before-master-refresh`.
- Read-only Langfuse spot-check: очередь Feature 181 содержит 50 pending observations; один вызов подтвердил `gpt-5.6-luna`, prompt `outline` v8, 3375/167 tokens, 5.25s model time и validated empty result. Подробности и ограничения — в `format-evaluation.md`.
- Candidate-only synthetic LiteLLM smoke после prompt corrections: 9/9 outcome formats schema-valid на v9; auto v11 с judge v12/v13 — faithfulness/action-items/completeness `1.0/pass`. Production labels не менялись.
- 2026-08-24 предыдущий полный version-bound candidate matrix до финального source-ref tightening: 18/18 schema/source-ref valid, mean `6.632s`, p95 `12.24s`, `46,942` tokens, но `4` hard-fail judge outcomes при `temperature=1`; последующий post-tightening matrix зафиксирован ниже.
- Предыдущая итерация prompt tightening через `gpt-5.6-luna` дала `18/18` schema/source-ref valid, mean `5.912s`, p95 `8.469s`, `194,272` tokens и `2` completeness judge events (`0.5`, `0.9`); после неё выполнен финальный candidate matrix ниже.
- Финальный candidate matrix после дополнительных format-specific corrections: outcome v23, judges v24/v25/v24, `18/18` schema/source-ref valid, `0` hard-fail judge outcomes, mean `2.972s`, p95 `3.988s`, `49,140` tokens; production labels не менялись.
- Независимая synthetic повторная проверка через remote operator LiteLLM route: `18/18` schema/source-ref valid, `50/50` применимых judge calls с score `1.0`, `0` failures; локальный compiler aggregate hash `060cdfb8b57edad75d96d88de2923ce0310d52486e2122d7b0fea1e39ed1fab6`. Это не заменяет held-out, version-bound Langfuse snapshot, Temporal/private real-meeting run или human usefulness evaluation.
- Exact Langfuse read-only compatibility check: candidate snapshots v23/v24/v25 доступны, но deployed API runtime до provider request требует удалённый из current config `max_completion_tokens`; это зафиксировано как release/deploy drift, prompt bypass не выполнялся.
- 2026-08-25 exact snapshot held-out rerun: `18/18` schema/source-ref valid, `50` applicable judge calls, `46` pass и `4` hard-fail, `judge_min=0`, `judge_mean=0.91`, outcome latency mean `6.916s`, p95 `13.719s`, `51,718` outcome tokens. Повторяемость hard-fail=0 не доказана.
- После следующего исправления eval accounting: prompt/optimizer unit suite `49 passed`, Feature 181 focused PostgreSQL suite `140 passed`, fast CI `1234 passed`; server lint и Python compile pass. Добавлен metadata-only usefulness/pairwise receipt validator, но его внешний human/private input ещё не запускался.

## Незакрытые gates

- T018 закрыт финальным suitable/unsuitable matrix. T031 остаётся открытой: held-out/human usefulness evaluation, version-bound full Temporal workflow и private real-meeting run не выполнены; prompt promotion не выполнялась.
- PR, Langfuse promotion, release и deploy остаются отдельными gates и требуют явного approval.
- GitHub issues остаются открыты до commit/PR evidence и provider-level quality gate.

## Latest current-worktree rerun

Дата: 2026-08-25

- Feature 181 focused suite после merge-refresh и исправления trusted-publication
  regression: `104 passed`, 2 warnings, exit 0.
- `infra/scripts/ci-local.sh --fast`: `1274 passed`, server lint pass, Python
  compile pass, exit 0; isolated PostgreSQL container удалён.
- Исправлено рассогласование slot-published outcome и legacy processing result:
  content-safe projection теперь сообщает `available`/`partial` только для
  active current default-slot outcome с той же media/processing revision,
  допустимым lifecycle/revision state и совместимым source hash.
- Авторизованная реальная запись проверена read-only: сохранённые разделы,
  format controls, current marker и source-jump controls отображаются. Новая
  provider generation в этом smoke не запускалась, чтобы не отправлять приватную
  расшифровку повторно.
- T031 остаётся открытой: version-bound Temporal/private real-meeting run,
  held-out human usefulness/pairwise evaluation и prompt promotion не выполнены.

## Current full-gate result

Дата: 2026-08-25

- `infra/scripts/ci-local.sh --full` завершился с `3533 passed, 1 skipped`,
  `1 failed`, 11 предупреждениями. macOS build/tests и contract validation
  прошли; единственный сбой — существующий timing test
  `test_sc017_one_hundred_warmed_atomic_consumptions_are_within_50ms_p95`
  (`52.68 ms` при пороге `50 ms`) в календарном контексте, вне изменённых
  файлов итогов.
- Повтор того же теста из изолированного focused PostgreSQL запуска прошёл:
  `1 passed, 34 deselected`; это подтверждает нестабильность измерения, но full
  CI остаётся `FAIL`, а не `PASS`.
- Feature 181 quickstart после текущих изменений прошёл: `113 passed`, 2
  ожидаемых предупреждения; контейнер PostgreSQL удалён wrapper-скриптом.
- T031 по-прежнему не закрыта: не выполнены version-bound Temporal/private
  real-meeting run и human-labelled usefulness/pairwise gate. Production
  prompt promotion, commit/PR, release и deploy остаются отдельными gates.

## Current-master refresh

Дата: 2026-08-25

- Ветка обновлена относительно `origin/master` `8f22aa9718ee2618b87dd98fae382b2aef471354`;
  перед merge сохранена локальная точка `codex/181-before-current-master-refresh-20260825`.
- После merge в миграционном графе обнаружены две heads: summary lifecycle и
  `0082_mediascribe_words`. Добавлена no-op merge-migration
  `0083_merge_summary_mediascribe`; `alembic heads` теперь возвращает
  только эту head.
- Актуальный Feature 181 focused matrix после merge: `173 passed`, 2
  ожидаемых предупреждения; сюда входят generation, dispatch, workflow, slots,
  prompts, UI, source contracts и trusted publication.
- Актуальный `infra/scripts/ci-local.sh --fast`: `1263 passed`, server lint и
  Python compile pass; контейнер PostgreSQL удалён wrapper-скриптом.
- Read-only Langfuse v4 UI (v4.17.0): 9 built-in outcome prompts доступны как
  candidate snapshots версии 23; текущий `production` label для них не
  перемещён. Evaluation Rules, Datasets и Experiments не содержат активных
  записей. Это подтверждает готовность к controlled promotion, но не заменяет
  project-side evaluator migration и production E2E.

## Current validation correction

Дата: 2026-08-25

- Full CI на исходном merge-коммите выявил контрактную ошибку длины Alembic
  revision ID в merge-миграции: `0083_merge_summary_and_mediascribe_heads`
  превышал лимит 32 символа. Revision сокращён до
  `0083_merge_summary_mediascribe`; имя файла и граф `down_revision` сохранены.
- После исправления focused migration/schema checks: `2 passed`, `2` ожидаемых
  предупреждения; `alembic heads` возвращает единственную head
  `0083_merge_summary_mediascribe`.
- `infra/scripts/ci-local.sh --fast`: `1263 passed`, server lint и Python
  compile pass, `2` ожидаемых предупреждения; контейнер PostgreSQL удалён.
- Предыдущий full CI больше не считается актуальным для release gate, потому
  что после него изменился commit. Full CI должен быть повторён на новом
  точном SHA.
- В повторном full CI на `641a2f19` основной parallel phase прошёл (`3529
  passed`, `1` skipped), но strict phase обнаружил загрязнение общей
  disposable RLS-БД: migration contract test оставлял synthetic summary slots,
  и последующий smoke-downgrade тест закономерно блокировался защитой `0076`.
  Изолированный прогон двух RLS-файлов после очистки fixture rows: `44 passed`,
  `2` ожидаемых предупреждения. Добавлена локальная очистка только этих
  synthetic slots перед проверкой unrelated downgrade operation; full CI нужно
  повторить на следующем SHA.

## Authoritative full gate after corrections

Дата: 2026-08-25

- Exact SHA: `baf3d8fd`.
- `infra/scripts/ci-local.sh --full`: PASS. macOS build и `767` Swift-тестов
  прошли; ContractValidation — PASS; parallel PostgreSQL phase — `3529 passed`,
  `1 skipped`; strict RLS phase — `52 passed`, `1 skipped`; server lint,
  Python compile, compose config и deployment evidence scan — PASS.
- Единственный оставшийся результат `blocked` внутри full gate — ожидаемая
  локальная RLS hardening boundary без production database; live production
  probe не выполнялся.
