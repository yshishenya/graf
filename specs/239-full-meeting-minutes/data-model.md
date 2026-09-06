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

Модель возвращает `transcript_segment_id`, `sequence` и `quote: string | null`.
Сервер добавляет из закреплённого сегмента `start_seconds`, `end_seconds`,
`speaker_label`, `source_role` и `evidence_kind=segment`.

Незнакомый id, неверная sequence, дубликат или несовпадающая непустая quote
отклоняют весь документ. Ни refs, ни части тезиса молча не удаляются. Решение
содержит `acceptance_source_refs[1..8]`, указывающие на окончательное принятие.
Семантическая проверка должна подтвердить, что эти реплики действительно
фиксируют согласие, а не только содержат слова из решения.

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

`MeetingOutcomeGenerationAttempt`, `GenerationCall` и `MeetingSummarySlot`
сохраняют текущие переходы:

```text
queued → generating → candidate → accepted
                    ↘ rejected | expired | stale
queued/generating → blocked_dependency | failed | ambiguous
```

Call 1 сохраняет validated draft. Call 2 сохраняет validated result envelope
`{verification, protocol, draft_hash}`; `protocol` — окончательный обогащённый
документ с frozen header. `validated_result_hash` хеширует весь envelope,
`MeetingOutcomeSet.content_hash` — только canonical JSON его `protocol`.
Publication proof связывает оба call id/result hashes, draft_hash, hash
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

## SemanticVerification

Второй вызов возвращает закрытый объект `verdict: pass | fail`,
`findings[]: {code, path, source_refs}`. Допустимые codes: unsupported_claim,
missing_topic, missing_decision, missing_action, wrong_owner, wrong_deadline,
proposal_as_decision, missed_correction, incoherent, insufficient_evidence.
`pass` допустим только с пустыми findings. Проверяющая модель не переписывает
черновик. Ответ и его hash сохраняются в GenerationCall sequence 2 вместе
с полным исходным transcript и точным draft в request_json. Сервер сверяет
draft hash, transcript hash, exact prompt/root и настройки обеих стадий.
Публикация требует завершённые call 1 и call 2 и валидный pass. При fail или
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

1. Каждая стадия имеет ровно одну логическую Generation Call; call 1 создаёт,
   call 2 проверяет. Повтор workflow использует сохранённые завершённые вызовы.
2. Полный transcript snapshot совпадает с pinned source hash.
3. Все refs каждого тезиса каноничны, вместе покрывают весь смысл; наличие
   ref не выдаётся за математическое доказательство семантики.
4. Сервер, а не модель, задаёт timestamps и destination.
5. Candidate owner-only; share/export accepted-only.
6. Старый плоский payload никогда не рендерится как новый протокол.
7. Обновление transcript/speaker attribution создаёт новую ревизию.
8. Удаление встречи сохраняет observability truth и удаляет контролируемый
   protocol artifact через текущий lifecycle.
