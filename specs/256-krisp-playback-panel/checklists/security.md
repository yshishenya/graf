# Проверка требований F256: security

Reviewer-owned. Исполнитель не отмечает пункты. Первый этап без ножниц.

- [x] CHK001 Определены ли owner/viewer/commenter/editor/summary-only и запрет автоматического повышения старых grants? [FR-011]
- [x] CHK002 Описаны ли повторная ACL/CSRF/RLS проверка каждой операции и принадлежность parent/source/media? [FR-011, SC-005]
- [x] CHK003 Однозначны ли version/request_id, лимиты текста/mentions и индексы Unicode? [data-model.md]
- [x] CHK004 Ограничено ли упоминание уже допущенным адресатом и нейтральным внутренним уведомлением без email/выдачи доступа? [FR-011]
- [x] CHK005 Полны ли требования к producer RLS, удалению, account merge, stale media и запрету текстов в логах? [FR-015/016, data-model.md]

Независимый reviewer `requirements_review`, 2026-09-08: CHK002/004/005 проходят
по contracts/comments.md и data-model.md «Права и жизненный цикл»; T005/T008
и quickstart.md требуют отрицательные проверки, очистку и account merge.
Повторный проход после исправлений: CHK001 закрыт по data-model.md44–51 и
contracts/comments.md41–42: новые права выдаёт owner/editor, прежний can_share
не повышает роль. CHK003 закрыт по data-model.md14–25 и contracts/comments.md43–46:
точный body без trim, code points, request_id для создания, expected_version
для edit/delete/resolution, идемпотентная реакция как явное исключение.
См. [requirements-review.md](../requirements-review.md). Это проверка требований,
а не подтверждение работающей защиты.
