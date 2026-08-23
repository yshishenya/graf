# Format evaluation

Дата: 2026-08-21

## Что подтверждено локально

- Все девять built-in форматов компилируются через production prompt compiler.
- У каждого формата есть отдельные Goal, Prioritize, Exclude и Render instructions.
- Safety fixtures используют canonical transcript JSON и явную untrusted-data boundary.
- Focused prompt suite: `18 passed` в последнем отдельном прогоне; тот же набор вошёл в общий PostgreSQL result `100 passed`.
- Hard-failure fixtures покрывают prompt injection, unsupported owner/date/decision, corrected/cancelled statements и invalid source references на уровне contract validation.

## Provider-level evaluation

Не выполнена и не заявляется:

```text
outcome_generation_enabled=false
litellm_url_configured=false
litellm_key_material_available=false
langfuse_configured=false
```

Поэтому в этой ветке нет честных данных о реальных model outputs, latency, token/cost, rubric scores или prompt promotion. T018 и T031 остаются открытыми до version-bound private run на разрешённых встречах. В git разрешено сохранить только counts, aggregate rubric scores, bounded failure codes и hashes — без transcript/output text, raw audio или private screenshots.

## Обязательный следующий gate

Для каждого формата нужны suitable и unsuitable cases, minimum faithfulness/owner/date/decision/actionability/type-fit scores и hard-fail=0. До этого prompt promotion, release-readiness claim и production deploy не разрешены.
