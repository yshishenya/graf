# Независимая проверка личного UI-действия

- [x] Существующие policy/notice copy и их редакции не изменяются.
- [x] Hydration и cookie другого аккаунта не являются личным согласием.
- [x] Accept/revoke требуют явного действия и серверной identity/version/CSRF проверки.
- [x] Ошибка не включает сбор и понятна пользователю.
- [x] Native changed сигнал не разрешает capture без серверного контекста.
- [x] Default-off и запреты broad providers сохранены.

Reviewer: см. [consent-ui-review.md](../consent-ui-review.md). Это requirement-quality, не runtime/UI readiness.
