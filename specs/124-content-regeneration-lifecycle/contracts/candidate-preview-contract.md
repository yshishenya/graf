# Contract: Candidate Preview and Cabinet Interaction

## Owner-only flow

```text
current accepted
   │ explicit format / Обновить итоги
   ▼
candidate queued → generating → ready
   │                         ├─ Использовать → atomic accept/supersede
   │                         ├─ Оставить текущие → current unchanged
   │                         └─ stale/expired/failed → recovery action
```

The current accepted outcome remains visible in every state. Candidate content
is never substituted into the current panel before accept.

## Polling behavior

- foreground polling uses bounded attempts/deadline and exponential backoff;
- hidden documents pause polling without cancelling server work;
- returning to the tab resumes from durable candidate state or offers `Проверить
  ещё`;
- session storage may remember only candidate ID, safe status, started time and
  non-sensitive route state; stale entries are pruned;
- after the bound, show `Вариант всё ещё готовится. Можно вернуться позже.` with
  `Проверить ещё` and `Обновить страницу`.

## Copy and accessibility

- ready: `Вариант «<формат>» готов`;
- generating: `Готовим вариант «<формат>»…`;
- conflict: `Итоги уже изменились` plus an explicit `Обновить` action;
- failure: concrete impact and `Повторить` where retryable;
- polite live region announces transitions without stealing focus;
- native buttons/links remain keyboard and VoiceOver reachable;
- shared viewers receive neither candidate status nor candidate actions.

## Preview safety

The preview endpoint/projection checks owner access and candidate lifecycle, never
returns provider secrets/raw diagnostics, and cannot mutate data. A preview URL
or candidate ID is not a share token and must fail closed outside the owner
scope.
