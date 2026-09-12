# Implementation Plan: Сохранение входа GRAF

**Branch**: `6795-persistent-app-session` | **Date**: 2026-09-11 | **Spec**: [spec.md](spec.md)

## Summary
Устранить подтверждённое суточное окончание входа: продлевать существующую AuthSession и срок того же cookie, включая нативные фоновые запросы.

## Technical Context
Python/FastAPI/SQLAlchemy/PostgreSQL; Swift/Foundation/WebKit. Существующие middleware, cookie helpers и DesktopUploadClient. Новых зависимостей и миграций нет.

## Risk and validation lane
High-risk product area: auth/sessions. Полный Spec Kit с clarify, независимой проверкой security checklist и analyze. Локально — целевые PostgreSQL и Swift tests. PR — governance-fast на точном SHA. Выпуск — release-full на замороженном SHA, dry-run и отдельное согласование production; установка GRAF Dev только после разрешённого коммита через harness.

## Constitution Check
До/после проектирования: PASS. Сохранены проверки пользователя/пространства/устройства, явный выход, секретность cookie и origin. Capture, AI и удаление встреч не изменяются. Legacy Impact: untouched; legacy_new=0, unowned_legacy=0, expired_exceptions=0. Независимый reviewer проверяет checklist перед кодом.

## Project Structure
- apps/server/src/twobrain_rec_server/auth/sessions.py: один срок по умолчанию 30 дней; условное продление действующей записи вместе с ограниченным по частоте учётом активности.
- apps/server/src/twobrain_rec_server/auth/dependencies.py: только после всех проверок, сохранить проверенный контекст в request.state; исключить logout. Окончательные зависимости ещё могут отклонить запрос.
- apps/server/src/twobrain_rec_server/auth/session_renewal.py: компактный middleware доставки срока, cookie для cookie-транспорта и X-GRAF-Auth-Expires-At для нативного транспорта; не переопределять cookie маршрута.
- apps/server/src/twobrain_rec_server/config.py и main.py: общий default и подключение middleware.
- apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift: единый обработчик успешного ответа передаёт срок в bridge, включая специальные прямые requestExecutor пути.
- apps/macos/RecApp/Sources/Cabinet/DesktopCabinetSessionBridge.swift: проверка origin/исходного токена/существующих cookie; только увеличение срока, обе копии, без создания после выхода и без auth-change при продлении.
- apps/server/tests/unit/test_auth_session_renewal.py, apps/macos/Shared/Tests/DesktopCabinetSessionBridgeTests.swift: воспроизводимая регрессия.

## Implementation phases
1. Документы, независимая проверка требований, analyze и GitHub задачи.
2. Регрессии → серверное продление → нативная доставка срока и проверки.
3. Проверка diff, converge, fragment, evidence. Не отмечать внешние gates выполненными до их выполнения.

## Complexity Tracking
Повторно используем существующий непрозрачный токен; отдельные refresh endpoints/таблицы/таймеры не нужны. Активность учитывается только после окончательного 2xx/304: последующий отказ scope/device не продлевает срок. Redirect продлевается на следующей успешной странице. Частота записи не более раза в пять минут; cookie можно повторно доставить без записи, чтобы восстановить потерянный ответ.

## Review follow-up — 2026-09-12

T007 уточняет реализацию FR-004 без изменения срока и пользовательского контракта. Перед отправкой разрешённой навигации основного фрейма нативное продление приостанавливается, поколение устаревает, уже отправленная запись WebKit завершается. Приостановка действует до окончания цепочки переходов и свежего согласования cookie; отмена, ошибка, загрузка файла и отключение представления освобождают только собственное состояние. Это общий барьер существующих embedded login/logout/space-switch форм; он не обещает атомарность независимых сетевых Set-Cookie. Будущий credential-changing fetch должен использовать тот же барьер до dispatch. Регрессии управляют порядком операций без случайных задержек.

Истечение проверяется при окончательном продлении. Запрос, допущенный до срока, может завершить операцию после срока, но не возобновляет истёкший вход; отдельная регрессия закрепляет эту существующую границу, серверная логика не меняется.
