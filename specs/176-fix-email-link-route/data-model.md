# Data Model: Стабильное подключение email в приложении

Новых persistent entities, полей, cookies, таблиц и миграций нет.

Исправление меняет только transient ownership навигации:

- **WebKit-owned action**: исходный non-GET request и HTML-ответ формы;
- **SwiftUI-owned document route**: безопасный GET document, который можно
  восстановить без повторения пользовательского действия.

Существующие email-link state, session, CSRF token, rate-limit records и
account-merge entities не меняются.
