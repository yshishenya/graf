# Security Checklist: meeting-summary-ux

- [X] UI не расширяет access policy, RLS, share scope или deletion semantics.
- [X] Source refs проходят через уже разрешённые server-side view models.
- [X] Blocked/non-available states не выводят outcome item text.
- [X] Не добавляются credentials, signed URLs, storage keys, raw audio или raw
  model response.
- [X] Candidate preview не заменяет accepted outcome без явного существующего
  acceptance flow.
- [X] Синтетические данные в screenshots/runtime evidence не раскрывают private
  meeting content.
