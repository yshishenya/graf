# Research: полезные итоги встреч

Дата доступа к публичным источникам: 2026-08-21.

## Decision 1: Итоги — рабочий артефакт, а не пересказ

**Decision**: общий результат начинается с outcomes, decisions, actions, open questions и risks. Хронология и evidence остаются вторичным уровнем.

**Rationale**: [Read.ai](https://www.read.ai/articles/how-to-summarize-a-meeting-methods-templates-ai-tools) рекомендует группировать по темам и выделять решения/действия вместо повторения transcript. [Atlassian Meeting Notes](https://www.atlassian.com/software/confluence/templates/meeting-notes) разделяет decisions, action items, owners и deadlines.

**Alternatives considered**: extractive first-segment summary; generic chronological outline. Они быстрые, но не достигают post-meeting goal.

## Decision 2: Существующие девять форматов сохраняются, но получают разные контракты

**Decision**: не расширять каталог в этом slice. У каждого встроенного формата фиксируются собственные акценты, исключения и критерии полезности; `Авто` остаётся консервативным универсальным вариантом.

**Rationale**: текущий каталог уже виден пользователям и совместим с saved template lineage. Публичный Krisp каталог подтверждает понятность type-specific templates, но exact prompts не раскрывает. Изменение состава сейчас увеличит migration/UI scope и не исправит корневой accepted-result defect.

**Alternatives considered**: добавить brainstorming, retrospective, decision record и planning. Они полезны, но требуют отдельного catalog/version decision после evidence.

## Decision 3: Один model call с format-specific evidence-first instructions

**Decision**: сохранить существующий один LiteLLM call и strict JSON/source validation, но заменить короткую `FORMAT_FOCUS` строку на полноценный format contract: goal, prioritize, omit, special classification rules и rendering order.

**Rationale**: [Anthropic prompt engineering](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/claude-prompting-best-practices) поддерживает explicit constraints, untrusted-data separation и extract-before-synthesize. Текущая schema уже требует source refs и локально валидируется. Отдельный двухпроходный pipeline дал бы больше кода, inference/cost и новую durable lineage без доказанной необходимости.

**Alternatives considered**: два model calls `typed extraction → renderer`; отдельная модель-классификатор типа встречи. Отложены до измеренного failure pattern.

## Decision 4: Детерминированный baseline не является пользовательским fallback

**Decision**: для новых revision-scoped meetings deterministic extraction не создаёт ready/accepted user outcomes. Если AI недоступен, UI показывает pending/blocked/error. Legacy accepted rows продолжают читаться для совместимости.

**Rationale**: текущий генератор копирует первый segment и regexp-matched whole segments, поэтому визуально воспроизводит «мокап». Лучше отсутствие результата с объяснением, чем неподтверждённая уверенность.

**Alternatives considered**: улучшить regex/heuristic. Это неизбежно остаётся transcript classification и будет ошибаться на модальности, отменах и reassignment.

## Decision 5: Первый automatic result остаётся кандидатом до подтверждения

**Decision**: `automatic_baseline`, manual format и refresh создают candidates. Только явное действие пользователя может сделать candidate принятым; source/deletion/access fences и expected-current CAS остаются обязательными.

**Rationale**: strict schema и exact source refs подтверждают форму и provenance, но не смысловую поддержку каждого claim, owner или date. Пока runtime faithfulness gate не откалиброван на реальных данных, system auto-accept превращает schema-valid hallucination или prompt injection в авторитетный результат. Candidate показывается сразу после обработки, поэтому генерация остаётся автоматической, а принятие — fail-closed.

**Alternatives considered**: auto-accept после schema-only validation; второй runtime judge call; всегда auto-replace. Первое недостаточно для semantic truth, второе требует отдельной durable lineage, cost/latency budget и provider-level calibration, третье разрушает trust/versioning.

## Decision 6: Quality gate — task-specific rubric плюс hard failures

**Decision**: использовать 0–4 rubric: faithfulness, attribution, temporal accuracy, decision accuracy, actionability, coverage/relevance, type fit, structure/usability, coherence/fluency, uncertainty handling. Critical unsupported fact, false owner/date/final decision, missing evidence или executed prompt injection — hard fail.

**Rationale**: [SummEval](https://aclanthology.org/2021.tacl-1.24/) даёт general dimensions, а [OpenAI evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices) рекомендует task-specific continuous evals и pairwise/pass-fail вместо vibe checks. Meeting-specific action/decision truth требует более строгих gates.

**Alternatives considered**: schema-only tests; single average score. Они пропускают критическую hallucination.

## Decision 7: Evidence-first и prompt-injection boundary сохраняются

**Decision**: transcript и personal template text всегда untrusted data; source refs обязательны; owner/date/decision требуют прямой опоры; unknown остаётся empty/not_inferable.

**Rationale**: [QMSum](https://aclanthology.org/2021.naacl-main.472/) и [MeetingBank](https://aclanthology.org/2023.acl-long.906/) поддерживают locate/ground before synthesis. [OWASP Prompt Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html) рекомендует отделять instructions от untrusted content и валидировать output.

**Alternatives considered**: цитаты только для decisions/actions. Отклонено: summary claims тоже должны быть проверяемыми.

## Format research summary

| Формат GRAF | Главный вопрос результата | Обязательные акценты | Недопустимый вывод |
|---|---|---|---|
| Авто | Что важно знать и сделать после встречи? | outcomes, explicit decisions/actions, open questions/risks | скрыто угаданный тип встречи |
| По темам | Как развивались содержательные темы? | тематический outline в порядке разговора, без filler | хронология приветствий и технической настройки |
| Протокол встречи | Что официально зафиксировано? | purpose/result, final decisions, commitments, next steps | предложение как принятое решение |
| Синхронизация проекта | Где проект сейчас и что мешает? | health evidence, progress, milestones, blockers, dependencies, asks | выдуманный green/yellow/red status |
| Еженедельная встреча команды | Что изменилось за неделю? | wins/progress, priorities, blockers, team actions, open questions | личные оценки как team status |
| Один на один | Что важно сотруднику и какая поддержка нужна? | themes, wins, workload, obstacles, feedback, mutual commitments | diagnosis/performance verdict без прямой опоры |
| Статус для клиента | Какую ценность/прогресс увидит клиент? | period, progress, evidence, risks, decisions/asks, next steps | internal speculation или upsell, которого не обсуждали |
| Интервью с кандидатом | Что кандидат фактически ответил? | question/answer themes, observed evidence, follow-ups | protected traits, invented score/hiring decision |
| Выявление потребностей | Какая проблема подтверждена, какие критерии соответствия названы и что согласовано дальше? | current state, pains/impact, explicit fit criteria/evidence, goals, constraints, stakeholders/process, objections, next step | guessed budget/authority/urgency/fit |

## Source-backed recheck: происхождение и качество prompt contracts

Дата повторной проверки: 2026-08-22.

### Что было источником текущего каталога

Каталог появился в Feature 121 и первоначально опирался на публичную категорию
Krisp и наблюдаемый template picker: Auto, Outline, Project Sync, Weekly Team,
1:1, Client Status, Sales, Hiring, Training, All Hands и Meeting Minutes. GRAF
не скопировал весь список: для первой версии были выбраны девять сценариев,
Training и All Hands не вошли, а Meeting Minutes был сохранён. Конкретные
`FORMAT_FOCUS`, schema, grounding и validation rules написаны для GRAF; Krisp
не публикует proprietary prompts, модели или результаты eval.

Официальная [Krisp Meeting Notes Templates](https://help.krisp.ai/hc/en-us/articles/26708055686044-Meeting-Notes-Templates)
подтверждает starter/personal templates, default и per-meeting выбор, а также
blocks для Action Items, Key Points и Outline. Она не подтверждает внутренний
prompt или factuality contract.

### Иерархия источников

1. **Высокое доверие**: официальная документация продукта, OpenAI Cookbook,
   нормативные документы и peer-reviewed papers.
2. **Среднее доверие**: активно поддерживаемый open source с лицензией, schema,
   source IDs и тестами, но без независимых semantic eval.
3. **Низкое доверие**: prompt collections, marketing copy без output contract,
   репозитории без лицензии или benchmark, использующий fake analyzer.

Prompt snippets не считаются «лучшими» по числу stars. Важны provenance,
grounding, deterministic validation и held-out evidence.

### Подтверждённый архитектурный baseline

Лучший найденный открытый baseline — официальный
[OpenAI Speaker-Aware Meeting Intelligence](https://developers.openai.com/cookbook/examples/audio/speaker_aware_meeting_intelligence/speaker_aware_meeting_intelligence)
и его [закреплённый notebook](https://github.com/openai/openai-cookbook/blob/79791c4e0dcc794d0110787805a5833c87092132/examples/audio/speaker_aware_meeting_intelligence/speaker_aware_meeting_intelligence.ipynb):

- stable segment IDs и speaker-aware transcript;
- transcript как untrusted evidence;
- strict structured output;
- отдельные decisions, actions, risks, explicit questions и suggested follow-ups;
- evidence refs для каждого элемента;
- `null`/empty вместо выдуманных owner/date/roles;
- механическая проверка evidence и human review перед важной записью downstream.

Старый [OpenAI meeting-minutes tutorial](https://github.com/openai/openai-cookbook/blob/79791c4e0dcc794d0110787805a5833c87092132/examples/data/oai_docs/meeting-minutes-tutorial.txt)
не является baseline: это legacy free-form GPT-4/Chat Completions пример без
schema, citations, provenance и eval.

Из GitHub полезны архитектурные идеи, а не текст для копирования:
[BasedHardware/omi](https://github.com/BasedHardware/omi/blob/8ec49fa7c3821c92da422977c00d1e94fa94ca1b/backend/utils/llm/conversation_processing.py)
использует explicit commitments, source IDs и unknown due;
[Meetily](https://github.com/Zackriya-Solutions/meetily/blob/0281737d87d26352fb0adc78c8c0975f691b23d1/frontend/src-tauri/src/summary/processor.rs)
показывает map/combine для длинного transcript;
[StenoAI](https://github.com/stenolabs/stenoai/blob/7c1cbb8532d67734f35cb8ecfaaf832f133e85/src/summarizer.py)
подтверждает map/reduce, но теряет evidence IDs. Коллекции из десятков и сотен
templates без eval не используются как quality authority.

### Что подтверждают конкуренты

- [Fellow](https://help.fellow.ai/en/articles/8981574-ai-meeting-recaps): summary,
  action items и decisions; templates связывают sections с timestamps.
- [Notion AI Meeting Notes](https://www.notion.com/help/ai-meeting-notes): key
  points, actions, speaker labels и citations с переходом к transcript.
- [Granola templates](https://docs.granola.ai/help-center/taking-notes/customise-notes-with-templates):
  purpose, detail, style и section structure зависят от meeting type.
- [Microsoft Teams intelligent recap](https://learn.microsoft.com/en-us/microsoftteams/intelligent-recap-calls-meetings):
  notes, recommended tasks, speakers, topics, chapters и key decisions.
- [Avoma Smart Templates](https://www.avoma.com/release-notes/introducing-smart-templates-prepare-agenda-instantly-and-get-ai-notes-consistently):
  shared custom categories для repeatable meeting types.

Ни один проверенный конкурент не публикует независимо подтверждённый
production prompt. Их документация подтверждает observable output contracts и
IA, но не даёт права считать скрытую реализацию эталоном.

### Академические выводы, которые влияют на GRAF

- [QMSum](https://aclanthology.org/2021.naacl-main.472/) показывает, что
  supporting spans часто несмежны; нужен полный coverage pass до synthesis.
- [Purver et al.](https://aclanthology.org/2007.sigdial-1.4/) определяет action
  item через публичное commitment; task, owner и timeframe могут быть
  распределены по диалогу.
- [FActScore](https://aclanthology.org/2023.emnlp-main.741/) и
  [ALCE](https://aclanthology.org/2023.emnlp-main.398/) поддерживают atomic
  claims и раздельную проверку claim support и citation quality.
- [Lost in the Middle](https://doi.org/10.1162/tacl_a_00638) требует отдельно
  проверять recall важных facts в начале, середине и конце длинной встречи.
- [MeetingBank](https://aclanthology.org/2023.acl-long.906/) оценивает
  informativeness, factuality, fluency, coherence и redundancy раздельно;
  хороший язык не доказывает factuality.
- [FairEval](https://aclanthology.org/2024.acl-long.511/) и исследования
  LLM-as-a-judge требуют human calibration и проверки position bias.

### Исправленная taxonomy

Верхний уровень остаётся компактным: Auto Recap, Minutes, Project Update,
Weekly Team, 1:1, Hiring Interview, Sales Discovery и Client Update. `Outline`
является способом представления, а не meeting type; в совместимом каталоге v1
он пока остаётся отдельным форматом, но называется `По темам`. Неоднозначные
названия уточнены: `Интервью с кандидатом` и `Выявление потребностей`.

Standup покрывается Weekly/Project. QBR, Retrospective, Workshop/Brainstorming,
Board/Executive, Training и All Hands отложены до подтверждённого спроса; их
нельзя добавлять только ради полноты списка. Research interview не смешивается
с hiring interview и требует отдельного будущего contract.

### Prompt и eval decision после повторной проверки

Grounded core v8 сохраняется: он соответствует основному OpenAI baseline и
академическим выводам. Новая версия prompt не создаётся только из-за найденного
в интернете wording. Сначала нужен open coding 30–50 representative
`GENERATION` observations, затем failure taxonomy и по одной минимальной правке
на подтверждённый failure class.

Judges не являются gate до human calibration на held-out labels. Для каждого
типа отдельно измеряются atomic support precision, decision/action precision и
recall, owner/date accuracy, source-ref precision, completeness, redundancy и
usefulness. Pairwise comparison запускается в обоих candidate orders.

Официальная [OpenAI evaluation guidance](https://developers.openai.com/api/docs/guides/evaluation-best-practices#example-summarizing-transcripts)
рекомендует production + expert reference data, held-out evaluation,
continuous eval и pairwise/classification/scoring вместо open-ended judge.
`gpt-5.6-luna` сохраняется как явно выбранный пользователем route для этих
тестов; официальная документация позиционирует Luna как более быстрый и
дешёвый вариант для простых задач, поэтому сложные длинные встречи нельзя
считать доказанно качественными без отдельного held-out результата.

Дополнительные источники: [Atlassian Project Status](https://www.atlassian.com/software/confluence/templates/project-status), [Atlassian 1:1](https://www.atlassian.com/blog/teamwork/running-successful-one-on-one-meetings), [HubSpot discovery](https://blog.hubspot.com/sales/discovery-call-questions), [CIPD selection methods](https://www.cipd.org/en/knowledge/factsheets/selection-factsheet/), [Scrum Guide](https://scrumguides.org/scrum-guide.html).

## Krisp clean-room comparison

Публичная документация [Meeting Notes Templates](https://help.krisp.ai/hc/en-us/articles/26708055686044-Meeting-Notes-Templates) описывает starter templates, personal templates, rich-text layout, Action Items/Key Points/Outline blocks, default template и switching per meeting. Наблюдаемый installed app держит template picker рядом с AI Notes и постоянным player.

Krisp публично предупреждает, что regeneration заменяет notes и теряет manual edits. GRAF сохраняет более безопасную candidate-before-replace модель. Exact Krisp prompts, model, schema, grounding и eval results неизвестны; они не копируются и не предполагаются.

## Evaluation dataset

- Synthetic: normal, no-decision, many proposals, corrected decision, cancelled/reassigned action, unknown owner/date, relative date, bad diarization, multilingual, long meeting, interruptions, contradictory statements, empty/noise, prompt injection.
- Authorized private: локально выбранные существующие встречи; содержимое и raw outputs не сохраняются в git, screenshots, issues или chat. Сохраняются только counts, aggregate scores, bounded failure codes и hashes.
- Every built-in format: suitable and unsuitable meeting. Unsuitable input must not fabricate format-specific facts.
