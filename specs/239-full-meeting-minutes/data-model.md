# Data Model: Полноценные итоги встреч

## MeetingOutcomeSet

Существующая immutable candidate/accepted revision получает единственный
содержательный документ:

- `protocol_schema_version: string | null` — версия закрытого JSON-договора;
- `protocol_state: processing | available | blocked | unavailable`;
- `protocol_json: object | null` — нормализованный сервером протокол;
- `content_hash` — SHA-256 canonical JSON документа.

`protocol_json = null` у исторической плоской ревизии не означает пустой
протокол. Такая ревизия требует повторной генерации по закреплённой
расшифровке.

## MeetingProtocol

```text
meeting_type
executive_summary[]: EvidenceStatement
objectives[]: EvidenceStatement
topics[]: MeetingTopic
decisions[]: EvidenceStatement
action_items[]: ActionItem
open_questions[]: EvidenceStatement
next_steps[]: EvidenceStatement
risks_and_constraints[]: EvidenceStatement
notes[]: EvidenceStatement
uncertain_sections[]: section name
```

Заголовок, дата/время, часовой пояс, язык, тип входа и список канонических
говорящих собираются сервером из Meeting/ProcessingResult/canonical speaker
model до первого вызова и сохраняются в immutable header snapshot кандидата.
При публикации этот снимок входит в protocol_json и content_hash. Рендерер
не перечитывает изменяемые Meeting/speaker поля; модель не угадывает metadata.

## EvidenceStatement

- `text: string` — один проверяемый тезис, 1..4000 символов;
- `source_refs: EvidenceRef[1..8]` — совокупность источников, покрывающая весь
  тезис без недоказанной причинности или согласия.

## EvidenceRef

Модель возвращает только `sequence: int >= 0` и `quote: string | null`.
UUID в модельном ответе — запрещённое дополнительное поле, а не второй
поддерживаемый формат. Сервер проверяет уникальность id и sequence полного
закреплённого источника. Модельные ответы и проверенные тела extraction,
draft и verification содержат только sequence/quote. Поле protocol в validated
result envelope третьего вызова содержит canonical UUID и времена; hash
третьего результата покрывает весь envelope. После успешной проверки
сервер добавляет из точно выбранного сегмента
`transcript_segment_id`, `start_seconds`, `end_seconds`,
`speaker_label`, `source_role` и `evidence_kind=segment`.

Неизвестная/нецелая/отрицательная sequence, дубликат или несовпадающая непустая quote
отклоняют весь документ. Ни refs, ни части тезиса молча не удаляются.
Повтор sequence запрещён внутри одного массива refs. Использование той же
sequence в других массивах refs разрешено. Решение
содержит `acceptance_source_refs[1..8]`, указывающие на окончательное принятие.
Семантическая проверка должна подтвердить, что эти реплики действительно
фиксируют согласие, а не только содержат слова из решения.
Source hash и ревизия ограничивают область sequence; индекс массива не
подменяет sequence. Publisher заново получает canonical id/time из того же
источника и сравнивает весь документ, поэтому подмена id после обогащения
не становится валидной из-за пересчитанного content hash.

## MeetingTopic

- `title: string`;
- `context[]`;
- `discussion[]`;
- `proposals_and_alternatives[]`;
- `outcome[]`.

Пустые необязательные подразделы не рендерятся. Тема без содержательного
тезиса недопустима. Одна тема может ссылаться на несмежные сегменты.

## ActionItem

- `task: string`;
- `owner_text: string | null`;
- `due_date_text: string | null`;
- `task_source_refs[1..8]`;
- `owner_source_refs[0..8]`;
- `due_date_source_refs[0..8]`.

`owner_text != null` требует `owner_source_refs`; `due_date_text != null`
требует `due_date_source_refs`. Generic speaker labels не являются людьми.
Относительный срок сохраняется буквально.

## Lifecycle entities

`PromptRootPromotion` — отдельная операторская строка общего допуска из
contracts/meeting-protocol.md §Допуск корневого комплекта F239 и dev. Она
хранит project/root/operation identity, неизменяемые полные root export,
activation и qualification с хешами, однократно финализируемый event и
текущее операционное состояние. Частичные unique indexes ограничивают
текущий допуск и незавершённое переключение одним на project/root.
Это не workspace-owned данные; у workers чтение, запись только maintenance.
Новый `GenerationCall.execution_authority_json/hash` сохраняет exact
ProductionAuthority либо EvaluationAuthority, отдельно от model request.
Authority остаётся в retained call после удаления встречи. Старые calls с
null authority могут доставить observations, но не исполнить новые стадии
или опубликовать новый протокол.

До появления этой операторской строки EvaluationAuthority хранит полный
export/Activation в неизменяемом run-owned снимке изолированной оценки.
Он создаётся до первого egress и не требует Qualification/Event. Production
loader читает операторский журнал, evaluation loader — run-owned снимок.
Связь отчёта с последующей Qualification проверяется по exact project/root/
version/export/activation/runtime. Полный закрытый metadata-only отчёт
создаёт finalize_run; его схема и правила приёма заданы в contracts.

`MeetingOutcomeGenerationAttempt`, `GenerationCall` и `MeetingSummarySlot`
сохраняют текущие переходы:

```text
queued → generating → candidate → accepted
                    ↘ rejected | expired | stale
queued/generating → blocked_dependency | failed | ambiguous
```

Call 1 сохраняет validated extraction. Call 2 сохраняет validated draft.
Call 3 сохраняет validated result envelope
`{verification, protocol, draft_hash, extraction_hash}`; `protocol` — окончательный обогащённый
документ с frozen header. `validated_result_hash` хеширует весь envelope,
`MeetingOutcomeSet.content_hash` — только canonical JSON его `protocol`.
Publication proof связывает все три call id/result hashes, extraction_hash, draft_hash, hash
документа, source/root и точных запросов. Публикация разрешена только при точном совпадении
этих данных и валидном pass. Accepted slot не меняется при
ошибке, stale source, deletion race или неизвестном provider outcome.

## Built-in format identity

Существующие ключи (`graf-auto-v1`, ...), default и slots сохраняются: это
идентификаторы, не переключатель старой реализации. Версия нового protocol
contract хранится отдельно. Текущие встроенные определения обновляются до
version 2; активной генерации и рендеринга версии 1 нет. Исторические
template snapshots остаются только неизменяемыми данными. Личные sections
отображаются по mapping в contracts без изменения их сохранённого порядка.

## FactualExtraction (внутренний результат модели)

Закрытый объект с обязательными массивами `facts` и `actions`; пустые массивы
разрешены, но не являются доказательством полноты или пригодности встречи.
Все записи создаёт модель по полному источнику в хронологическом порядке.

`facts[]`:

- `kind`: context | argument | proposal | decision | question | risk | constraint | correction;
- `text: string` и `source_refs[1..8]`;
- `status`: stated | tentative | conditional | confirmed | rejected | cancelled | uncertain;
- `acceptance_source_refs[0..8]`, обязательные для confirmed decision.

`actions[]` повторяет поля ActionItem и добавляет:

- `commitment_status`: proposed | committed | conditional | cancelled | uncertain;
- `due_status`: absent | tentative | conditional | agreed | uncertain.

Разговорное смягчение в контексте принятой задачи не отменяет обязательство
и названный срок: допустимы `commitment_status=committed`, `due_status=agreed`
и краткий срок без частицы смягчения. Модель определяет это по полному контексту,
не по наличию отдельного слова; реальные условия, отказы и переносы сохраняются.
Исходная формулировка доступна по refs. `due_status=absent`
требует null срока и пустых refs; другое значение — текст срока и refs.
Owner null требует пустых owner refs. Отмены и поправки остаются фактами,
а не удаляются сервером. Лимиты: 500 facts, 200 actions, 4000 символов в
смысловом поле; превышение отклоняет весь ответ, не обрезает его.
Подтверждение смысловой классификации остаётся задачей модели и содержательной
приёмки. Структурный validator проверяет форму, null/ref соответствие и точную
принадлежность refs/quotes закреплённому источнику, не редактирует слова.

Extraction не является публичным итогом и не попадает в `protocol_json`,
share или exports. Он сохраняется только в существующем GenerationCall с
полным transcript/request/raw response/result, без новой таблицы.

## SemanticVerification

Третий вызов возвращает закрытый объект `verdict: pass | fail`,
`findings[]: {code, path, source_refs}`. Допустимые codes: unsupported_claim,
missing_topic, missing_decision, missing_action, wrong_owner, wrong_deadline,
proposal_as_decision, missed_correction, incoherent, insufficient_evidence.
`pass` допустим только с пустыми findings. Проверяющая модель не переписывает
черновик. Ответ и его hash сохраняются в GenerationCall sequence 3 вместе
с полным исходным transcript и точным draft в request_json. Сервер сверяет
draft/extraction hashes, transcript hash, exact prompt/root и настройки всех стадий.
Verifier получает полный transcript и draft, но не extraction. Публикация
требует завершённые call 1, 2, 3 и валидный pass. При fail или
неоднозначном egress candidate не готов; автоматического model retry нет.
Новая попытка — новая явно созданная candidate identity.

## Инварианты

Config contract 5 и root v3 определены в contracts/meeting-protocol.md.
HTTP request, `attempt.model_parameters` и generator hash используют одну
проекцию pinned snapshot из Langfuse. Generation/verifier могут выбирать
разные модели. Completed call с изменёнными настройками не переиспользуется.
`actual_model/provider` nullable и согласованы с retained raw response;
requested alias не подставляется вместо отсутствующего фактического значения.
Исторические JSON/hashes не меняются; новая SQL-миграция для этих nullable
полей не требуется. Retained observation delivery не исполняет старый root.
Исторические header-only actual поля сохраняются без новой проверки raw-body;
она относится только к сохранению и публикации новых calls, не к общей
проверке хешей и доставке retained records (см. contracts/meeting-protocol.md).

1. Каждая стадия имеет ровно одну логическую Generation Call; call 1 извлекает,
   call 2 синтезирует, call 3 проверяет. Повтор workflow использует сохранённые
   завершённые вызовы, повторно валидируя всю цепочку без inference.
2. Полный transcript snapshot совпадает с pinned source hash.
3. Все refs каждого тезиса каноничны, вместе покрывают весь смысл; наличие
   ref не выдаётся за математическое доказательство семантики.
4. Сервер, а не модель, задаёт timestamps и destination.
5. Candidate owner-only; share/export accepted-only.
6. Старый плоский payload никогда не рендерится как новый протокол.
7. Обновление transcript/speaker attribution создаёт новую ревизию.
8. Удаление встречи сохраняет observability truth и удаляет контролируемый
   protocol artifact через текущий lifecycle.
