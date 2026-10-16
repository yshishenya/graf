# Независимая проверка требований режима без PostHog backup

Requirement quality, не production acceptance. Reviewer owns checkboxes/report.

- [x] Решение владельца и риск невосстановимой потери аналитики явно записаны; новые копии отменены, существующие не удаляются.
- [x] Конституционное исключение узкое: только минимальный PostHog; продуктовые backup и release/deploy gates сохранены.
- [x] Default required, допустимые значения и fail-closed invalid scope описаны; campaign/Yandex не получают исключение.
- [x] Missing/stale/failed backup/restore остаются truthful metadata, не фиктивными receipts; required rollback возвращает blockers.
- [x] Retention365/access/MFA/legal/consent/noIP/delivery/retry/dedupe обязательны; generic capture исключён.
- [x] T110/issue7472, focused verification, independent review/exact CI и отдельные production gates определены.

Независимое ревью 2026-10-04: PASS, checked=6, unchecked=0. Доказательства и границы: [posthog-no-backup-review.md](../posthog-no-backup-review.md). Отметки подтверждают качество требований, не реализацию или готовность production.
