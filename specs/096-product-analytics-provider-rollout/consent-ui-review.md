# Независимая проверка требований consent UI

Дата 2026-10-03, reviewer header_review. Только новый UI срез; исторический broad collection не переоценивается.

Прочитан appended plan §Доступное личное действие и consent-ui checklist. Пять пунктов подтверждены: unchanged notice/version; account-scoped choice/no hydration acceptance; trusted button action+authenticated identity/version/CSRF; bare native changed только для server refresh; default-off/no broad collection. Они не подтверждают работающую реализацию.

## Неподтвержденный пункт

«Ошибка не включает сбор и понятна пользователю»: plan обещает закрытый server gate на любой ошибке. Это нельзя гарантировать для потерянного PUT response после commit или failed withdrawal при ранее accepted state. Требуется точно разделить local/native closed state, подтвержденное сервером состояние и unknown/previous server state; показать человеку неподтвержденный отзыв и путь retry/readback. Не считать ошибку HTTP доказательством отсутствия записи consent. Перед implementation это clarity blocker, без необходимости новых полномочий.

При повторной проверке expected user identity/version должны проверяться под тем же user row lock непосредственно перед записью. Native gate следует инвалидировать до запроса, а не только после successful response.

Повторно прочитан checklist: 5 [x], 1 [ ]. Итог BLOCKED до уточнения ошибочного/неопределенного PUT. Только checklist и этот report изменены; code/spec/plan/tasks/remote не менялись. Runtime consent и production не аттестованы.

## Повторная проверка уточнения

Plan прочитан повторно. Прежний clarity blocker устранен: local/native закрывается до PUT; ambiguous failure не называется закрытым server state; сообщение различает неподтвержденное сохранение/отзыв и дает повтор; persisted choice не восстанавливает consent. Identity/acceptance-version проверяются под row lock, withdrawal сохраняется при off/readiness/stale. Это подтверждает ранее открытый пункт.

Текущий verdict PASS требований, 6 [x], 0 [ ] после повторного чтения checklist. Исторический BLOCKED выше superseded данным уточнением; runtime proof/implementation не подтверждены. Код и другие artifacts reviewer не менял.
