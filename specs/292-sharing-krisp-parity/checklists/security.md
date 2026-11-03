# Security requirements review — reviewer-owned

- [x] SEC001 Определены ли scopes/default и неизменность старых ссылок без автоматического расширения? [spec FR-003/004/006; data-model]
- [x] SEC002 Определены ли actor/tenant/CSRF/версия/fence для изменений и повторный resolver для каждого чтения/audio? [spec FR-005/009; contracts]
- [x] SEC003 Ограничены ли публичные поля и запрещены ли hidden transcript/audio для summary-only, private metadata и owner impersonation? [spec FR-008/026; data-model; contracts «Единый проигрыватель FR-026»]
- [x] SEC004 Описаны ли expiry/revoke/rotate/scope/deletion гонки, Range, лимит памяти и безопасные ошибки/headers/logs? [spec FR-009/012/020; quickstart]
- [x] SEC005 Определены ли добровольные invitations/membership, идемпотентность и неизвестный исход доставки? [spec FR-005/019; data-model]
- [x] SEC006 Определены ли строгие native inputs, собственная сессия, Dev/production и безопасный TTL возврата без токена в login URL? [spec FR-010/021; contracts]
- [x] SEC007 Есть ли предметные negative/regression/runtime проверки и граница выпуска? [spec FR-015/023; plan; quickstart]

## Фактические ворота выпуска FR-027

- [ ] SEC008 Подтверждены ли для выпуска exact-SHA/base PR checks, frozen train/candidate, единственный authoritative release-full, go decision, cd dry-run/execute/health/rollback и Developer ID/notarization/stapling/Gatekeeper/Sparkle/public readback? [FR-027; T013/T015–T017; release-and-validation.md; macos-notarization.md]. Причина: проверенный validation.md не содержит этих доказательств нового выпуска; T012/T013/T015–T017 открыты. Требования к воротам определены, их фактическое прохождение не подтверждено.
- [x] SEC009 Сохраняет ли фактическое копирование выбранную аудиторию без неподтверждённого расширения доступа? [FR-003/006/024; US2.5; contracts UX; T018; review-report R1]. Требования PASS; узкая фактическая сверка исправления PASS: invite_only/workspace возвращаются до любых API mutations и копируют защищённый маршрут; Chromium/WebKit отрицательные проверки, отмена публикации, повторное copy и clipboard fallback подтверждены. Повторная сверка T019/R2 также PASS: надпись закрытой аудитории не обещает продление/замену. Это не PASS установленной/публичной версии: полная живая приёмка остаётся UX008, выпуск — SEC008.

Результат независимой проверки: см. [review-report.md](../review-report.md). SEC001–SEC007 относятся к качеству требований; SEC008 отдельно отражает фактические ворота выпуска. Требования выпуска проверены; итоговая приёмка реализации и выпуска не завершена.
