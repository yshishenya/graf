# Security Requirements Checklist: подключение email

- [x] Требование запрещает replay mutating request как GET.
- [x] Существующие session, CSRF, rate-limit и one-time-code границы явно сохранены.
- [x] Account linking/merge правила находятся вне изменения и остаются fail-closed.
- [x] Email, code, token, nonce и private identifiers исключены из route и evidence.
- [x] Same-origin desktop header contract сохранён.
- [x] GET fallback для POST-only endpoint явно отвергнут.
- [x] Production validation использует синтетические данные и metadata-only evidence.
