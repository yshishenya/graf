# Privacy and safety review — владелец: рецензент

- [X] CHK001 Разделены ли настройки уведомлений, OS permission и capture authorization? [FR-004/011/012]
- [X] CHK002 Исключены ли утечки после logout/scope change/delete/revoke? [FR-009/011]
- [X] CHK003 Однозначны ли auth, CSRF, scope и native bridge? [contracts/notifications]
- [X] CHK004 Сохранён ли Stop при сетевой/авторизационной ошибке? [FR-003]
- [X] CHK005 Запрещены ли произвольные URL/команды из payload? [FR-009]
- [X] CHK006 Полны ли dedup, read-revision race, event-after-commit? [FR-007/008]
- [X] CHK007 UI-история не меняет аудит, удаление и обязательную доставку? [FR-016]
- [X] CHK008 Достаточны ли условия legacy удаления, миграции и отката? [FR-015]

- [X] CHK009 Исключены ли local incidents из web inbox и серверные события из нативной доставки, включая embedded, другой Mac и смену владельца? [FR-020; surface-separation]

Независимая проверка требований: [review-evidence.md](../review-evidence.md).
Отметки не подтверждают прохождение приёмки реализации.
