# Contract: meeting-outcome-value

## 1. Automatic quality candidate

При первом imported result с `transcript_status=available`, `segment_count>0` и
включённой outcome generation policy сервер:

1. сохраняет/reuses deterministic accepted baseline;
2. выбирает exact active workspace built-in default;
3. создаёт/reuses `automatic_baseline` AI attempt;
4. создаёт/reuses durable dispatch intent;
5. завершает processing без ожидания Langfuse/LiteLLM/Temporal network I/O.

Если policy выключена, transcript непригоден, default invalid или dependency
недоступна, accepted baseline и transcript не блокируются. Состояние кандидата
truthful; implicit paid retry/second call не создаётся.

## 2. Prompt policy

Outcome prompt обязан:

- считать transcript и custom template untrusted data;
- сначала выбрать итоговые atomic claims, затем category states;
- кратко описывать результат встречи, исключая greeting, agenda-only, filler и
  повторения;
- отличать финальное решение от предложения/обсуждения/вопроса;
- отличать обязательство от идеи/пожелания/условного действия;
- применять последнюю явно подтверждённую correction;
- не выводить owner/due без прямой опоры; generic/unknown speaker не становится
  человеком;
- сохранять относительную дату как сказано без выдуманной calendar date;
- прикладывать 1..8 непосредственно поддерживающих refs к каждому item;
- соблюдать detail budget и не заполнять пустые разделы общими фразами;
- вернуть только strict response schema.

## 3. Runtime output validation

Candidate целиком rejected, если:

- item не имеет source ref;
- ref отсутствует в pinned transcript, повторён или sequence не совпадает;
- category/state parity нарушена;
- owner/due находятся не у action;
- item/category/sequence/field bounds нарушены;
- response incomplete, invalid JSON/schema, refused, stale или oversize.

Semantic entailment проверяется prompt/eval и человеком до accept; локальный
validator не заявляет, что string ID сам по себе доказывает claim.

## 4. Candidate preview API

Existing endpoint:

`GET /api/v1/cabinet/meetings/{meeting_id}/summary-candidates/{candidate_id}/preview`

остаётся owner-only и `private, no-store`. Каждый item возвращает structured
refs, вычисленные из pinned transcript:

```json
{
  "category": "action_items",
  "text": "…",
  "owner_text": "…",
  "due_date_text": "…",
  "truth_label": "supported",
  "source_refs": [
    {
      "transcript_segment_id": "uuid",
      "sequence": 12,
      "start_seconds": 42.5,
      "end_seconds": 49.1,
      "source_role": "incoming",
      "seekable": true
    }
  ]
}
```

Internal category keys не выводятся в UI. Порядок: summary, action_items,
decisions, затем secondary. Preview даёт два исхода: «Оставить текущие» и
«Использовать».

## 5. Evidence interaction

- Button существует только при разрешённых transcript и playback destination.
- Activate переключает detail tab, обновляет hash, seek player, переносит focus
  к exact segment и объявляет изменение.
- Без destination отображается plain bounded source label; listener-less button
  запрещён.
- Summary-only никогда не раскрывает transcript text/timestamps сверх уже
  разрешённого projection contract.

## 6. Shared/readiness UX

- Summary-only browser entry возвращает HTML и reuse localized accepted summary
  projection.
- Viewer/share/export никогда не читают unaccepted candidate.
- Non-ready summary имеет один aggregate localized state.
- Meeting list различает как минимум: «Итоги готовы», «Расшифровка готова ·
  итоги готовятся», «Нужна проверка», «Обработка»; unknown не равен «Готово».

## 7. Eval and promotion

`GRAF-MEETING-EVAL/1.0.0` pin'ит dataset, prompt, schema, model, judge и code
versions. Critical unsupported decision/action/owner/due, wrong attribution или
injection success обнуляет пример. Held-out promotion использует worst-example
gate; mean сохраняется как diagnostics. Evidence в git содержит только fixture
IDs, hashes, counts, metrics и bounded error codes.

Изменённые outcome/control prompts создаются без `production`. Label mutation
требует private held-out pass, human-calibrated judges, expected-source check,
operator approval, protected mutation readiness и rollback target.
