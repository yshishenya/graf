# Research: доверенные версии и meeting intelligence

## Method and evidence limits

Исследование объединяет: read-only разбор GRAF Feature 181/182 и текущего
outcomes stack; black-box аудит установленного KRISP по обычному
пользовательскому интерфейсу; полное исследование промптов и его сравнительный
разбор из Codex task `01a02b3a-b966-7083-b339-709862f4346f`; публичную
документацию Langfuse/Temporal/OpenAI; MeetingBank/QMSum; публичный GEPA
repository. Бинарники KRISP, private API, протоколы и model behavior не
исследовались.

Скриншоты KRISP содержат приватные данные и остаются только в
неверсионируемых локальных evidence bundles вне git. В спецификацию попадают
только metadata, наблюдаемые interaction contracts и агрегированные counts.

## Decision 1 — Простая продуктовая модель: одна актуальная версия per type

**Decision**: пользователь не принимает обычную генерацию вручную. Для каждого типа сохраняется одна актуальная ревизия; переключение сохранённых типов не вызывает inference; refresh заменяет только свой тип после автоматической проверки.

**Rationale**: снижает decision load, соответствует ожиданию «функция работает сама», сохраняет last-known-good и близко к проверенному interaction pattern KRISP — type/template picker находится рядом с notes, а notes воспринимаются как готовый продуктовый результат.

**Alternatives considered**:

- Обязательный candidate review/accept: безопасен, но заставляет пользователя регулярно выполнять работу QA.
- Одна глобальная current summary: не позволяет хранить полезные представления разных типов.
- Генерировать при каждом переключении: медленно, дорого и непредсказуемо.

## Decision 2 — Canonical intelligence отделяется от представлений

**Decision**: Feature 194 создаёт одну evidence-backed knowledge model встречи; типы итогов являются versioned projections, а не девятью независимыми «правдами».

**Rationale**: MeetingBank использует divide-and-conquer с привязкой summary passages к сегментам длинной встречи; QMSum показывает ценность locate-then-summarize и разных query-oriented представлений. Общий extraction/resolve слой предотвращает расхождение решений, owners и дат между типами.

**Alternatives considered**:

- Девять полноценных prompt calls прямо из transcript: проще локально, но решения и действия расходятся между форматами.
- Один огромный universal prompt: плохо тестируется, трудно версионируется и перегружает контекст.

## Decision 3 — Prompt является bundle, а не монолитом

**Decision**: будущий runtime компилирует exact bundle:

```text
graf/meeting-intelligence/core
+ source-context-policy
+ one exact ProfileContractCatalogV1 + resolved CompositeProfileContractV1
+ one exact AutoSectionMappingPolicyV1 when template_key=auto
+ typed audience/focus/detail/privacy/facts-only controls
+ generic phase/<extract|resolve|verify|repair|auto-resolve|profile-projection|presentation-synthesis|presentation-verify>
+ exact structured-output schema
+ deterministic layout renderer version
```

Per-profile Langfuse prompts are explicitly forbidden. Profile semantics live
only in exact catalog bodies; generic projection/presentation prompts consume
the complete resolved composite as typed data. Auto additionally uses one
deterministic, hash-bound mapping that keeps the visible shell at
`Action Items → Key Points` while the hidden intent profile affects only
selection, priority, criticality and safety.

Каждый run пинит versions/hashes, `gpt-5.6-luna` LiteLLM route, request
parameters и validator/schema versions. Искусственный max output limit
4048/4096 не задаётся; действуют phase-specific schema envelopes и проверенные
infrastructure limits.

Receipt V1 принимает только literal `analysis_mode=facts_only`. Любой
model-authored analysis откладывается до отдельной product phase и требует
новых verifier scope, resolved-run manifest, rendered-content, publication
receipt и projection-policy versions; он не может быть включён настройкой
существующего V1 bundle.

**Rationale**: compact core обеспечивает общие non-invention/evidence rules;
profile отвечает за тип встречи; projection policy — за аудиторию, фокус и
детализацию; фазовые prompts проще оценивать и чинить. Transcript и supporting
materials всегда untrusted evidence, не инструкции. Актуальное официальное
руководство GPT-5.6 рекомендует precise goal/constraints/output contract,
удаление повторов, сохранение только измеримо полезных примеров и проверку
изменений на representative evals. Для reasoning-capable GPT-5 также
рекомендуется задавать цель, сильные ограничения и explicit output contract,
не расписывая лишние промежуточные шаги. Это поддерживает компактный bundle
вместо монолита.

**Alternatives considered**:

- Prompt в коде: нарушает Langfuse authority и усложняет promotion/rollback.
- Свободный custom prompt пользователя: prompt-injection и непредсказуемая схема.
- DSPy как второй runtime: не нужен до доказанной нехватки существующего stack.

## Decision 4 — Deterministic checks first; calibrated semantic gates mandatory

**Decision**: schema validity, source-ref existence, exact owner/date constraints,
duplicate/contradiction rules and stale/deletion/prompt-revocation checks run
deterministically first. Every model-generated canonical claim then requires a
calibrated semantic-entailment result. Criticality controls omission and
non-droppable behavior, while source→candidate and candidate→canonical
critical-omission verification are also mandatory over one deterministic,
gap-free `SourceVerificationCatalogV1`. The
semantic verifier is not a source of truth and cannot override failed
deterministic checks; uncalibrated, invalid or unavailable verification fails
publication closed. Utility/style judges remain diagnostic until calibrated.

**Rationale**: Langfuse рекомендует сначала error analysis: около 100 representative generations, open coding 30–50, затем 5–10 реальных failure classes. Без этого judge оптимизирует предположения команды. Независимый аудит текущего optimizer обнаружил отсутствие per-class TPR/TNR, paired baseline comparison и per-format non-regression.

**Alternatives considered**:

- Один composite judge score: скрывает critical failure за средним.
- Judge-only publication: допускает correlated hallucinations.
- Только human review каждого production output: слишком дорого и возвращает decision load пользователю.

## Decision 5 — Paired baseline/candidate evaluation

**Decision**: promotion сравнивает production bundle и candidate на одних frozen held-out items с одинаковыми model settings. Требуются zero critical regressions, per-format non-inferiority, paired quality/cost/latency deltas и blinded human preference на выборке.

**Rationale**: абсолютный threshold позволяет худшему кандидату пройти, если оба варианта выше порога. Langfuse experiments дают comparable dataset runs, но GRAF хранит immutable owner-controlled manifest с exact dataset/evaluator/bundle versions.

## Decision 6 — GEPA только после устойчивого evaluator contract

**Decision**: GEPA используется позже как operator-only offline research после Feature 200. Он не auto-promote production и не вводит DSPy. JEPA исключается: это representation learning, а не prompt optimization для этой задачи.

**Rationale**: GEPA оптимизирует заданную metric/feedback; слабый judge приведёт к эффективному judge gaming. Сначала нужны taxonomy, frozen splits, calibrated judges, paired baseline и bundle rollback.

## Decision 7 — Temporal V2 изолирован очередями и типизированными границами

**Decision**: Feature 195 сначала закрывает доказанные P1/P2 проблемы текущего
durable path, затем запускает новый `MeetingOutcomePipelineV2` только на трёх
выделенных Task Queues: interactive, automatic и background. V1 и V2 Workers не
poll одну unversioned queue; V1 остаётся до replay/drain gate. Все Workflow и
Activity boundaries получают один Pydantic input и один result с явной версией,
а client/Workers используют один закреплённый `pydantic_data_converter`.

**Required before V2**:

- response reaching GRAF сохраняется до lifecycle projection;
- inference retry authority принадлежит только Temporal: OpenAI
  `max_retries=0`, LiteLLM `num_retries=0`, gateway/provider/transport automatic
  retries выключены; ambiguous HTTP outcome никогда не повторяется без
  durable proof of pre-egress failure;
- cancellation/abandoned-child semantics;
- aggregate Temporal History budget, не только per-chunk limit;
- real replay fixtures, V1 replay + queue-drain + zero-open removal gates, V2
  queue isolation and PINNED Worker Deployment ramp/current/rollback;
- serialization/replay старых typed payloads и converter parity;
- Priority/Fairness учитываются как Public Preview: self-hosted readiness
  требует effective read-back `matching.useNewMatcher=true`,
  `matching.enableFairness=true`, `matching.enableMigration=true` и
  backlog-migration fixture; недоказанная capability оставляет выделенные
  очереди и measured custom weighted-fair scheduler как fallback;
- Langfuse pending→sending→confirmed|ambiguous delivery accounting по единому логическому
  GenerationCall без exactly-once/upsert обещания.

**Rationale**: Temporal workflow code должен быть deterministic, all I/O in
Activities, retries owned by Temporal. Отдельный Workflow Type без отдельной
queue всё ещё может попасть несовместимому Worker; queue isolation — минимальный
полный routing contract. Pydantic boundary фиксирует сериализацию и допускает
только additive defaults без молчаливого replay drift.

## Decision 8 — KRISP: authorized observable reference fidelity

**Decision**: Constitution 5.0.0 authorizes Feature 196 to reproduce the
observable Krisp UX/UI/IA literally: Notes/Transcript context, inline type
picker, quick/full catalog, persistent player, timestamp evidence, action-item
structure, loading/error/short-meeting states, visible copy, layout, component
geometry, palette, typography and icon treatment.

**Rationale**: the product owner chose a proven reference over mandatory visual
novelty. GRAF still uses independently written code and does not reuse extracted
assets, binaries, private APIs/protocols, secrets, private content or
proprietary model behavior. Accessibility, trust-critical product truth and
third-party asset, logo or trademark rights may require documented deviations;
approved functional UI labels and interaction microcopy may match literally.

## Decision 9 — Prompt research is specification input, not copied runtime text

**Decision**: ни один найденный GitHub/Reddit/Medium/master prompt не объявлен
«лучшим» и не загружается целиком. Исследование используется как каталог
requirements; runtime остаётся короткой phase-specific композицией. Canonical
phases запрещают profile/audience/privacy/focus/detail/output-language controls;
Auto/projection/presentation получают только разрешённые строки закрытой
inclusion matrix. Primary + optional secondary сначала детерминированно
компилируются в один `CompositeProfileContractV1`. Название секции вроде
`objections` или `root_cause` недостаточно: каждый `ProfileContractV1`
включает полный hash-bound `SectionContractV1.semantic_rule`, а composite
body/hash без изменений входит в projection, synthesis, verification,
rendered-content identity и publication receipt. Отдельных
`profile/<profile>` prompts нет: они создали бы второй источник истины.
Stable `MasterPromptClauseRegistryV1` содержит gap-free hash partition всего
791-строчного source snapshot для provenance и отдельный requirement-atomic
register: каждая нормативная source-группа имеет exact lines/source hash,
normalized requirement/hash, clauses, disposition и decision code, а unlisted
research narrative/headings/examples/citations явно non-runtime. IDs map every transferred
requirement to runtime prompt, deterministic policy/renderer, explicit rejection
or deferred versioned feature; exact `ProfileContractV1` bodies and held-out
profile×applicable-clause cells prove that modular compilation did not silently
drop it.

Повторный architecture audit обнаружил ещё один неочевидный цикл: measured
task/eval evidence не может одновременно называть candidate root и входить в
hash этого root. Поэтому root `ActivationManifestV1` содержит executable
definitions и preregistered plans, а complete measured
`ProfileClauseEvalResultSetV1`/`TaskStabilityEvidenceV1` связываются с уже
созданным root во внешнем immutable `RootQualificationRecordV1`. Успешное
движение protected label подтверждается отдельным `RootPromotionEventV1`;
runtime authority — root + activation + полная typed immutable binding на
promotion event, не один prompt label и не bare digest. Binding остаётся вне
root/activation body, но проходит через все requests/calls/manifests/receipts и
каждый раз позволяет заново получить и проверить event/qualification bodies.

**What transfers**:

- closed source-authority rules for transcript/chat/agenda/attachments;
- distinction between accepted/preliminary/requires-approval/deferred/cancelled/
  superseded decisions, proposal/idea/option dispositions and personal commitments;
- evidence-backed effective dates and closed uncertainty handling;
- action only for commitment, explicit assignment or accepted addressed
  request; an unknown owner/date remains semantically unknown and is omitted from
  canonical JSON rather than emitted as `null`; acceptance criterion, dependency and
  status transfer only when independently supported;
- trusted-or-explicitly-unknown speaker attribution, exact numbers/units and
  conflicting variants, plus relative-date normalization only from a pinned
  meeting date/timezone while retaining the original wording;
- free-form `my_name_and_role` is rejected as identity, speaker mapping,
  ownership or authorization input; those facts come only from authenticated
  GRAF subject and trusted participant mapping, and generated subject-scoped
  results remain Feature 208;
- meeting intent, mixed-audience least-privilege intersection, privacy, focus,
  bounded detail, exact evidence-display mapping and facts-only default;
- contradiction/correction handling and evidence refs;
- outcome-first thematic/scannable presentation with deterministic empty-section
  handling rather than a chronological transcript or mandatory null-filled table;
- Retrospective, Executive/Board, Incident, Training and Formal Minutes profile
  requirements plus separate no-diagnosis/no-hiring-recommendation, blameless/
  confirmed-root-cause, no-idea-to-action and no-unproved-legal/sales clauses;
- version-bound human review for policy-required sensitive external or
  system-of-record egress, never for ordinary on-screen reading;
- optional continuity and follow-up draft as separate non-canonical products;
- no routine clarification questions: mark gaps and continue safely.

**What does not transfer**:

- the 500+ line monolithic master prompt;
- mandatory tables full of `не указано`;
- inferred owners, deadlines, risk severity or mitigation;
- undefined/free-form `privacy_mode`; V1 accepts only the closed deterministic
  `PrivacyPresentationPolicyV1` data-class × materiality × mode action matrix
  that can narrow but never widen authorization;
- source situation/default preset tables as runtime selection authority; they
  remain research examples while GRAF uses one versioned product policy;
- independent full-transcript extraction for every summary type;
- one composite judge score or automatic prompt promotion.
- repeated judges over one frozen task output as a claim of model stability;
  five fresh full-pipeline runs and separate judge stability are both required.
- model self-review as publication evidence; every transferred clause instead
  needs deterministic checks and/or blinded human-calibrated held-out evidence.

The V1 follow-up draft is deterministic assembly from already verified visible
decisions/actions/open questions. A model-authored rewrite is not implied by the
research and requires a separately versioned/verified phase before it can ship.

**Source confidence**:

1. Official OpenAI meeting-intelligence/Structured Outputs/evaluation guidance
   defines the strongest technical grounding and guardrail baseline.
2. Official Langfuse experiment/error-analysis/calibration documentation defines
   the prompt iteration and evaluation process.
3. MeetingBank and QMSum support long-meeting divide-and-conquer and
   query/profile-oriented views.
4. Krisp black-box evidence validates the user journey and presentation model,
   not its hidden prompts or factual quality.
5. GitHub, Reddit and Medium are idea sources only; several popular recipes
   explicitly infer owners/deadlines and are rejected where they conflict with
   stronger evidence.

Checked GitHub recipes from the source prompt study:

- `github/awesome-copilot/skills/meeting-minutes/SKILL.md`: useful section and
  meeting-minutes workflow ideas; any inferred ownership remains disallowed.
- `zerostring-tech/promptchef/content/prompts/meeting-summarizer.md`: useful
  compact summary/action structure; no grounding or calibration authority.
- `sgharlow/claude-code-recipes/recipes/Recipe-001-Meeting-Notes-to-Action-Items.md`:
  useful action extraction shape; its context/implied-owner behavior is rejected
  by GRAF's explicit-evidence rule.

## Decision 10 — explicit current-source pointer before regeneration

**Decision**: Feature 194 establishes one same-workspace
`MeetingCanonicalSourcePointer`; Feature 197 mutates it through its fenced
transcript-regeneration transaction. Summary/transcript runtime truth cannot use
`latest_processing_result` ordering after cutover.

**Rationale**: repository inspection found multiple current-source reads routed
through a latest ProcessingResult query while outcomes already bind a concrete
`processing_result_id`. A language-regeneration result can race ordinary
processing or publication; ordering by version/time does not provide one
transactional winner. An explicit composite-bound pointer, locked before any
summary slot, gives expected-source CAS, stable publication checks, unambiguous
fan-out and a testable legacy migration. The existing historical rows remain the
content ledger; no transcript content is copied into the pointer.

## Decision 11 — ID selection is not presentation quality

**Decision**: после canonical extraction/resolve/verification и ID-only profile
projection нужны две отдельные model phases:
`presentation_synthesis → presentation_verify`. Synthesis формулирует и
локализует только selected canonical IDs; verify независимо проверяет каждое
statement, числа, отрицания/modality, decision/action state, translation и
полноту critical IDs. Deterministic renderer отвечает только за section order,
pagination, evidence links, static labels и UI markup.

**Rationale**: прежняя схема `ID-only projection → deterministic prose
renderer` могла выбрать правильные факты, но не могла качественно сделать
связное «Главное за минуту», естественную профильную формулировку или перевод.
Требование `output_language` внутри canonical core одновременно ломало
language-independent reuse. Скрытая переформулировка в renderer была бы
неobserved model behavior и обходила GenerationCall/Langfuse/receipt gates.

Официальная GPT-5.6 guidance подтверждает lean prompt, один раз сформулированные
hard constraints, explicit output contract и representative evals. Поэтому
каждая presentation phase имеет короткий самостоятельный prompt, strict schema,
derived numeric envelope, собственные GenerationCall/Temporal Activity/
Langfuse generation и receipt binding. Failed verification оставляет прежний
current result; fail receipt не создаётся.

Связанные identity-решения:

- `output_language` отсутствует в canonical phases и применяется только в
  synthesis;
- `focus=topic` — discriminated union с raw typed query, normalized
  value/version и resolved canonical topic IDs во всех identities/manifests/
  receipts/content hashes;
- shared-slot Receipt V1 rejects generated `my_actions`/`private_self`; Feature
  183 has no positive `my_actions` path, while Feature 205/196 may later add an
  authenticated zero-inference filter only after canonical actions and trusted
  subject mapping exist; Feature 199 rejects generated private output and only
  Feature 208 may later own a subject-scoped generation/receipt contract;
- exact Auto metadata/catalog/coverage descriptor, full-input hash and any
  validated result/selection proof are frozen in the attempt-owned
  `ResolvedRunManifestV1`; the full canonical profile view comes only from the
  immutable parent artifact and model-call request, never from later-mutated
  title/participants/duration or a sampled kind-count summary.

## Decision 12 — Auto is evidence assessment plus deterministic selection

**Decision**: Auto does not ask a model to return a final type from title,
duration and kind counts. `AutoResolverInputV1` supplies one complete bounded
canonical profile view (IDs, kind/state/text, typed relations and trusted roles;
no raw transcript). `AutoResolverResultV1` returns one strict evidence-backed
assessment for every row in the policy's complete `all_policy_rows` set; only
the compatible subset participates in ranking. A versioned deterministic policy alone
computes primary, optional compatible secondary and confidence, with stronger
eligibility for high-stakes profiles and conservative `general_summary` on ties,
insufficient evidence or a full view that does not fit the proven route
envelope. Partial sampling is forbidden.

**Rationale**: the earlier title/duration/kind-count input could not reliably
distinguish project, sales, research and incident meetings, and an always-general
resolver could pass a safety-only check. Separate input/result schemas, full
claim/relation coverage, closed reason codes, deterministic selection and
per-profile/pairwise/calibration/fallback gates make both specialization and
safe fallback testable. This is a GRAF product contract synthesized from the
source research; it is not copied from a community prompt or inferred from
Krisp's hidden model behavior.

Langfuse documentation currently confirms immutable numeric prompt versions,
labels, protected-label RBAC, version fetch and rollback by moving a label. It
does not document native expected-source CAS for label movement. GRAF therefore
uses a composed promotion protocol: one authorized writer/lock, expected-root
read/compare, root-bound qualification record, protected-root-label move, exact
read-back and immutable promotion event; mismatch leaves runtime on
last-known-good root+activation+typed event binding. This is an application guarantee, not a
claimed Langfuse primitive.

The 2026-08-23 documentation recheck also confirms that prompt config is
versioned arbitrary JSON, local cache may briefly serve an older version, and
the SDK can return an explicit fallback prompt. GRAF therefore accepts cache
only after exact numeric version/hash verification and rejects SDK fallback as
publication authority. Prompt availability never weakens bundle identity.

Langfuse's Datasets page now documents timestamp-version fetch and experiments
over that fetched version, while the Experiments-via-SDK page still states that
experiments run on latest. The owner-controlled item/hash manifest plus pre/post
read-back remains required. Langfuse also documents one dataset-item occurrence
per run, so stability repetitions use separate runs.

Langfuse v4 is observation-first; trace-level evaluators are deprecated, with
Cloud cutover documented for 2026-11-16. Annotation queues accept mutable trace,
observation or session membership, and evaluator versions created under an
existing name may automatically move active rules. GRAF therefore freezes its
own queue/evaluator manifest, targets the exact logical-root or named phase
observation, and prevents candidate evaluator creation from silently changing a
production rule.

## Sources

- [OpenAI speaker-aware meeting intelligence](https://developers.openai.com/cookbook/examples/audio/speaker_aware_meeting_intelligence/speaker_aware_meeting_intelligence)
- [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [OpenAI models](https://developers.openai.com/api/docs/models)
- [OpenAI model optimization](https://developers.openai.com/api/docs/guides/model-optimization#write-effective-prompts)
- [OpenAI prompting guidance for GPT-5.6](https://developers.openai.com/api/docs/guides/prompt-guidance-gpt-5p6)
- [OpenAI prompt engineering for current GPT-5 models](https://developers.openai.com/api/docs/guides/prompt-engineering#prompting-current-gpt-5-series-models)
- [OpenAI reasoning-model prompting advice](https://developers.openai.com/api/docs/guides/reasoning#advice-on-prompting)
- [OpenAI evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices#example-summarizing-transcripts)
- [Langfuse Experiments via SDK](https://langfuse.com/docs/evaluation/experiments/experiments-via-sdk)
- [Langfuse experiment data model](https://langfuse.com/docs/evaluation/experiments/data-model)
- [Langfuse datasets and timestamp versions](https://langfuse.com/docs/evaluation/experiments/datasets)
- [Langfuse annotation queues](https://langfuse.com/docs/evaluation/evaluation-methods/annotation-queues)
- [Langfuse prompt config](https://langfuse.com/docs/prompt-management/features/config)
- [Langfuse prompt availability and fallback](https://langfuse.com/docs/prompt-management/features/guaranteed-availability)
- [Langfuse prompt version control and labels](https://langfuse.com/docs/prompt-management/features/prompt-version-control)
- [Langfuse v4 observation-first model](https://langfuse.com/docs/v4)
- [Langfuse LLM-as-a-Judge and observation-level evaluation](https://langfuse.com/docs/evaluation/evaluation-methods/llm-as-a-judge)
- [Langfuse trace/observation structure best practices](https://langfuse.com/docs/observability/best-practices)
- [Langfuse error analysis](https://langfuse.com/guides/cookbook/error-analysis-llm-applications)
- [Langfuse judge calibration](https://langfuse.com/guides/llm-as-a-judge-calibration-skill)
- [Temporal Task Queue priority and fairness](https://docs.temporal.io/develop/task-queue-priority-fairness)
- [Temporal Worker Versioning](https://docs.temporal.io/production-deployment/worker-deployments/worker-versioning)
- [Temporal Worker Deployments](https://docs.temporal.io/production-deployment/worker-deployments)
- [MeetingBank](https://arxiv.org/abs/2305.17529)
- [QMSum](https://arxiv.org/abs/2104.05938)
- [GEPA](https://github.com/gepa-ai/gepa)
- [GitHub Awesome Copilot meeting-minutes skill](https://github.com/github/awesome-copilot/blob/main/skills/meeting-minutes/SKILL.md)
- [PromptChef meeting summarizer](https://github.com/zerostring-tech/promptchef/blob/main/content/prompts/meeting-summarizer.md)
- [Claude Code Recipe 001: meeting notes to action items](https://github.com/sgharlow/claude-code-recipes/blob/main/recipes/Recipe-001-Meeting-Notes-to-Action-Items.md)
- [Krisp Meeting Notes Templates help entry](https://help.krisp.ai/hc/en-us/articles/26708055686044-Meeting-Notes-Templates) — sitemap/public entry plus black-box installed-app observation; page fetch was access-blocked during this run.

## Evidence classifications

- **Observed**: конкретные KRISP screens/states, metadata/static capability
  wiring установленного пакета, текущий GRAF code/tests, branch/worktree state.
- **Documented**: public Langfuse/OpenAI/Temporal/GEPA/academic sources.
- **Product decision**: per-type saved revisions, no mandatory accept, exact GRAF IA and feature sequencing.
- **Not observed**: hidden Krisp prompt/model/ranking/server pipeline; none of
  these is treated as prompt authority for GRAF.
- **Unproven until implementation**: real `gpt-5.6-luna` quality, latency/cost,
  calibrated judge performance, provider ambiguity handling, Langfuse delivery
  confirmation/duplicate rate and production UX task success.
