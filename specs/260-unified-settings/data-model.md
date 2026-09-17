# Data Model

Миграций нет. Меняется представление существующих сущностей.

| Entity | Authority | Поля и правила |
|---|---|---|
| SettingsCategoryView | cabinet | id/label/group_label/icon/href, существующие разделы |
| Recording target/rule | native registry + MeetingDetectionSettingsStore | id/name; always/ask/never; новый target=ask; bulk только текущим допустимым |
| Notification preferences | DesktopNotificationPresenter + прежний store | reminders Bool, offsetMinutes 0/1/5, showTitles Bool, sound Bool; текущий owner на Mac |
| Authorization | UNUserNotificationCenter | checking/notDetermined/denied/authorized/unknown; отдельно от reminders |
| Account notifications | сервер | optional_email_enabled, optional_in_app_enabled, version и CSRF |
| Bridge context | native, временный | nonce документа + auth generation; invalidation при навигации/auth/detach/crash |
| Save state | текущий UI | loading → confirmed → saving → confirmed/error/unconfirmed |

Смена owner инвалидирует pending старого контекста; новый аккаунт читается заново. Нет credentials/owner ID/содержимого встреч в bridge response. Theme/timezone/locale сохраняют текущую область аккаунта, не переобъявляются локальными настройками.
