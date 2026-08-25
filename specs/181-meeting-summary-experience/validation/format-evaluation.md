# Format evaluation

Дата: 2026-08-24

## Что подтверждено локально

- Все девять built-in форматов компилируются через production prompt compiler.
- У каждого формата есть отдельные Goal, Prioritize, Exclude и Render instructions.
- Safety fixtures используют canonical transcript JSON и явную untrusted-data boundary.
- Focused prompt suite: `18 passed` в последнем отдельном прогоне; тот же набор вошёл в общий PostgreSQL result `100 passed`.
- Hard-failure fixtures покрывают prompt injection, unsupported owner/date/decision, corrected/cancelled statements и invalid source references на уровне contract validation.

## Provider-level evaluation

2026-08-24 выполнен разрешённый synthetic/private smoke через server-side secret
из текущего worktree: Langfuse Cloud EU read-only fetch production snapshots и
LiteLLM `https://litellm.pro-4.ru` с route `gpt-5.6-luna`. Ни один production
label не изменялся, prompt promotion не выполнялась.

Production baseline v5: 18/18 результатов schema/source-ref valid, но при
старом production judge было 10 hard-fail judge outcomes. Это baseline, а не
кандидат для продвижения.

Предыдущий полный matrix из 9 форматов × 2 кейса (до финального tightening
source-ref rules) дал:

- `18/18` schema-valid и `18/18` source-ref-valid;
- mean latency `6.632s`, p95 `12.24s`, `46,942` total tokens;
- `4` hard-fail judge outcomes при `temperature=1`; набор нестабилен между
  повторными прогонами, хотя targeted reruns отдельных исправленных классов
  проходили.

После tightening targeted reruns для `meeting-minutes`, `client-status-update`
и `sales-discovery` дали `1.0`; отдельный five-repeat sales probe дал `5/5`
faithfulness pass. Финальный полный post-tightening matrix дал `18/18`
schema/source-ref valid, mean `5.912s`, p95 `8.469s`, `194,272` tokens, но
осталось `2` completeness judge events со scores `0.5` и `0.9`. Это означает,
что prompt candidate всё ещё не доказал требуемую стабильность и не готов к
promotion. T018/T031 остаются открытыми до повторяемого hard-fail=0, held-out
набора, human usefulness rubric и version-bound Temporal/private run.
В git сохраняются только counts, aggregate scores, bounded failure codes и
prompt hashes — без transcript/output text, raw audio или private screenshots.

## Read-only Langfuse spot-check

2026-08-24 в авторизованном Langfuse UI проверена существующая очередь
`2026-08-22 Feature 181 Open Coding - Meeting Outcomes`: `50` элементов,
все со статусом `Pending`; разметка не изменялась. Один generation observation
проверен только по metadata и структуре результата:

- model: `gpt-5.6-luna`;
- prompt: `graf/meeting-outcome/outline`, version `8`;
- model duration: `5.25s`; workflow subtree: `16.37s`;
- usage: `3375` input, `167` output, `3542` total tokens;
- cost: `$0.000875`;
- validated result: `0` items, все `8` category states — `not_inferable`.

Это подтверждает, что Langfuse/LiteLLM/Temporal трасса и фактический model
route работают, но не является quality evaluation: это отдельная read-only
проверка, без изменения очереди и без сохранения содержимого в git/evidence.

## Candidate prompt smoke через реальный LiteLLM route

2026-08-24 выполнен изолированный synthetic smoke текущего prompt compiler и
LiteLLM endpoint `https://litellm.pro-4.ru` с моделью `gpt-5.6-luna`. Production
labels не изменялись и не продвигались.

- Candidate snapshots после отключения лимитов: outcome v9, затем v10 и v11
  после prompt corrections; judge snapshots v10/v11, затем v12/v13 после
  correction judge applicability.
- Все девять outcome formats на candidate-v9: `9/9` schema-valid; latency
  `9.963–22.260s`, mean `13.179s`; total usage `25,436` tokens.
- На первом общем judge pass было `5/9` hard-fail, но часть failures была
  ложной: action-items judge применялся к форматам, где action_items не входит
  в requested sections.
- После исправления prompt и judge contract повторный auto candidate-v11:
  `10` items, все `8` category states available; faithfulness, action-items и
  completeness — `1.0/pass`. Проверены corrected date, exact source refs,
  owner/date, conditional fallback как risk и unresolved pricing.
- Вызовы не печатали и не сохраняли transcript/model text; сохранены только
  bounded aggregate metadata и prompt hashes.

Это всё ещё не закрывает T018/T031 полностью: отсутствуют held-out сравнение,
human usefulness rubric и полноценный Temporal workflow run на version-bound
isolated workspace, а повторяемый hard-fail=0 не достигнут.

## Финальный candidate matrix после prompt tightening

2026-08-24 выполнен повторный полный matrix через реальный LiteLLM route
`gpt-5.6-luna` с unlabelled snapshots: outcome v23, faithfulness v24,
action-items v25 и completeness v24. Для каждого из девяти форматов проверены
suitable и unsuitable synthetic cases; все вызовы прошли через текущий compiler,
strict schema validation и реальные judge calls. Production labels и traces не
изменялись и не продвигались.

- `18/18` schema-valid и `18/18` source-ref-valid;
- `0` hard-fail judge outcomes; все применимые judge scores `1.0/pass`;
- mean latency `2.972s`, p95 `3.988s`, total usage `49,140` tokens;
- targeted outline rerun: `3/3` pass; targeted interview rerun: `2/2` pass;
- `temperature=0` отдельно проверен и отклонён самим LiteLLM route; pinned
  config с `temperature=1` сохранён, токеновые лимиты не добавлялись;
- в evidence сохранены только counts, aggregate scores, bounded failure codes,
  latency/token aggregates и prompt versions — без transcript/output text.

Это закрывает scope T018. T031 остаётся открытой до held-out сравнения,
human usefulness rubric и version-bound полного Temporal/private run на
разрешённой встрече; prompt promotion, release и deploy по-прежнему запрещены.

## Обязательный следующий gate

Для T031 нужны held-out сравнение, human usefulness rubric, version-bound
Temporal/private run и aggregate usefulness gaps. До этого prompt promotion,
release-readiness claim и production deploy не разрешены.

## Независимая повторная проверка через operator LiteLLM route

2026-08-24 выполнен ещё один независимый synthetic smoke из текущего worktree.
Использован remote operator-контур LiteLLM внутри `litellm-litellm-1`; секрет
из контейнера не выводился и не сохранялся. Вызовы шли на `gpt-5.6-luna` без
`max_completion_tokens`; production labels Langfuse не читались и не менялись.

- `18/18` suitable/unsuitable synthetic cases прошли strict schema и exact source-ref validation;
- `50/50` применимых judge calls вернули score `1.0`, `judge_min=1.0`, `judge_mean=1.0`;
- `0` provider, schema или source-validation failures;
- current local prompt compiler snapshot aggregate hash:
  `060cdfb8b57edad75d96d88de2923ce0310d52486e2122d7b0fea1e39ed1fab6`;
- raw transcript, candidate output, judge feedback и credentials не попали в
  stdout/evidence.

Это усиливает provider-route signal, но не закрывает T031: этот запуск использовал
version-bound к локальному compiler snapshot (outcome version `1`), а не к
точным unlabelled Langfuse versions `v23/v24/v25`; Temporal workflow/private
real-meeting run и human-labelled usefulness/pairwise baseline comparison не
выполнялись. Поэтому promotion и release gate остаются закрытыми.

## Exact Langfuse snapshot compatibility check

При read-only проверке deployed API container exact snapshots действительно
читаются из Langfuse (`outcome v23`, judges `v24/v25/v24`), но вызов через
deployed runtime остановлен до provider request с `KeyError: max_completion_tokens`:
его старый `PromptSnapshot.litellm_request` всё ещё требует этот ключ, тогда как
кандидатный config contract v2 намеренно его не содержит. Это подтверждает
несовместимость deployed runtime с текущим candidate contract; это не quality
failure модели и не основание для обхода контракта. До отдельного release/deploy
синхронизации exact Langfuse version-bound Temporal/private run остаётся
заблокированным.

## Exact snapshot held-out rerun

2026-08-25 выполнен read-only rerun на текущем маршруте LiteLLM с exact
Langfuse snapshots: outcome `v23`, faithfulness `v24`, action-items `v25`,
completeness `v24`; модель `gpt-5.6-luna`; `max_completion_tokens` не
передавался. Использованы `9 × 2` synthetic held-out cases, содержимое в
stdout/evidence не выводилось.

- `18/18` schema-valid и `18/18` source-ref-valid;
- `50` применимых judge calls, `46` pass, `4` hard-fail;
- `judge_min=0`, `judge_mean=0.91`;
- outcome latency mean `6.916s`, p95 `13.719s`, `51,718` outcome tokens;
- ошибки распределились по semantic coverage, а не по provider/schema: в
  targeted rerun наблюдались action/owner/date и completeness coverage gaps;
- повторяемость не доказана: другой rerun на том же exact set изменил failure
  profile. Поэтому LLM judges пока не считаются calibrated human gate.

Эта проверка усиливает evidence реального пути prompt snapshot → LiteLLM →
`gpt-5.6-luna`, но T031 не закрывает: отсутствуют human-labelled usefulness
и pairwise baseline comparison, полноценный version-bound Temporal/private run
и стабильный hard-fail=0. Production labels, prompt promotion и deploy не
изменялись.

## Контракт следующего quality gate

В текущем worktree добавлен проверяемый metadata-only validator для T031:

- принимает оценки usefulness только в диапазоне `1..5` по всем девяти built-in
  форматам;
- считает median usefulness и долю результатов, пригодных без регенерации;
- считает candidate-vs-baseline preference отдельно от ties и требует, чтобы
  pairwise строки содержали и `candidate-first`, и `baseline-first` порядок;
- возвращает aggregate значения и gap до порогов SC-005/SC-006 без transcript,
  output или комментариев разметчика.

Unit-проверка этого контракта и GEPA metric-call accounting: `49 passed`.
Это только готовность к безопасному подсчёту evidence; human labels, private
real-meeting run и version-bound Temporal run в текущем запуске не выполнялись,
поэтому T031 остаётся открытой.

## Current real-record read-only smoke

Дата: 2026-08-25

На авторизованной реальной записи без изменения данных проверены экран итогов,
переключатель формата, current marker, кнопка обновления и source-jump controls.
В UI были видны сохранённые итоговые разделы и полный format dialog. Одновременно
processing endpoint отдавал устаревшее `not_requested` из legacy
`ProcessingResult`, хотя current summary slot уже был опубликован. Исправление
в `processing/status.py` теперь сверяет current default slot, active/accepted
outcome, ту же media/processing revision и совместимый source hash, после чего
отдаёт `available`/`partial` только при подтверждённом совпадении.
Focused regression и fast CI после исправления зелёные. Новая генерация на
реальной расшифровке не запускалась в этом smoke, поэтому transcript/output
содержимое и provider egress в evidence отсутствуют.

## Current Langfuse v4 snapshot compatibility re-check

Дата: 2026-08-25

- Langfuse Cloud EU project UI reported v4.17.0. Read-only SDK inspection of
  the production label found v5 for each of the 10 allowlisted outcome prompt
  names, with legacy `config_contract_version=1` plus
  `max_completion_tokens`.
- The current contract deliberately accepts only the no-cap v2 outcome shape
  for new production candidates; v5 therefore fails validation before any
  provider call. This is intended fail-closed behavior, not a provider quality
  result.
- Exact unlabelled candidate v23 snapshots for all 10 names passed the current
  validator and were hashed without recording prompt or transcript content.
  Candidate v23 routes to `gpt-5.6-luna` and has no token cap. No Langfuse
  label, evaluator, dataset, experiment or annotation item was changed.
- This check does not prove a private real-meeting run. It remains blocked until
  an approved candidate-root/production-label promotion, a runtime deploy with
  outcome generation enabled, and an authorized real-record execution are
  available.
