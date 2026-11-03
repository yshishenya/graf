# Security requirements review — reviewer-owned

- [x] SEC001 Определены ли scopes/default и неизменность старых ссылок без автоматического расширения? [spec FR-003/004/006; data-model]
- [x] SEC002 Определены ли actor/tenant/CSRF/версия/fence для изменений и повторный resolver для каждого чтения/audio? [spec FR-005/009; contracts]
- [x] SEC003 Ограничены ли публичные поля и запрещены ли hidden transcript/audio для summary-only, private metadata и owner impersonation? [spec FR-008; data-model]
- [x] SEC004 Описаны ли expiry/revoke/rotate/scope/deletion гонки, Range, лимит памяти и безопасные ошибки/headers/logs? [spec FR-009/012/020; quickstart]
- [x] SEC005 Определены ли добровольные invitations/membership, идемпотентность и неизвестный исход доставки? [spec FR-005/019; data-model]
- [x] SEC006 Определены ли строгие native inputs, собственная сессия, Dev/production и безопасный TTL возврата без токена в login URL? [spec FR-010/021; contracts]
- [x] SEC007 Есть ли предметные negative/regression/runtime проверки и граница выпуска? [spec FR-015/023; plan; quickstart]

Результат независимой проверки: см. [review-report.md](../review-report.md). Отметки относятся только к качеству требований; итоговая сверка tasks выполнена; приёмка реализации не выполнена.
