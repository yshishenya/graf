# Implementation Plan: F292 — поделиться встречей

**Branch**: `codex/292-sharing-krisp-parity` | **Date**: 2026-11-03 | **Spec**: [spec.md](spec.md)

## Summary

Повторить весь наблюдаемый путь Krisp с собственным кодом GRAF: окно владельца, адресные права и общий доступ, полная страница получателя, первое приглашение и начало работы, переход в приложение. Старые ссылки F286 остаются только на сохранённые итоги. Решения и пределы сравнения: research.md.

## Technical Context

**Language/Version**: Python >=3.13, Swift (существующий Package.swift), JavaScript/CSS/Jinja.
**Primary Dependencies**: существующие FastAPI/Pydantic/SQLAlchemy/cryptography, SwiftUI/WKWebView. Новых зависимостей нет.
**Storage**: существующий PostgreSQL/MeetingShareGrant/PublishedMeetingSummary, серверное хранилище аудио; миграция для scope не нужна.
**Testing**: pytest, существующие node browser tests, Swift shared tests, живой браузер и единственный GRAF Dev.
**Risk / Validation Lane**: high-risk-product — публичный доступ, приватность, авторизация и reference fidelity.
**Release Gate**: пользователь 2026-11-03 явно поручил завершить проверку и выпустить новый production-релиз. После quickstart/converge и exact-SHA/base governance-fast/macos-pr/pr-metadata: линейный merge, CalVer metadata, frozen release train, один authoritative release-full, cd dry-run/execute, Developer ID/notarization/stapling/Gatekeeper/Sparkle и проверка опубликованной версии. Разрешение не заменяет эти ворота.
**Target Platform**: сервер Linux, браузеры 320/390/1440 px, macOS GRAF Dev/production схема.
**Project Type**: существующий web-service + desktop-app.
**Performance Goals**: аудио максимум 4 MiB буфера потока на публичный ответ; общий предел nginx 30 r/s burst60 сохраняется. Не загружать аудио до действия пользователя (preload metadata/none). Длинная расшифровка не создаёт вторую БД-копию.
**Constraints**: без токенов/содержимого в evidence; RLS workspace и lock встречи; no-store/no-referrer/noindex; отказ вместо повышения прав; F286 идемпотентность не меняется.
**Scale/Scope**: одна активная ссылка/встреча; существующие пределы адресатов; viewer публично, повышенные роли адресно.

## Constitution Check

До исследования и после проектирования: PASS по требованиям. Системный звук и ручные start/stop не затрагиваются; AI/MediaScribe credentials не переносятся; хранение и удаление используют действующие сущности. Публичная проекция явно ограничена, авторизация повторяется при каждом чтении; приглашения не отправляются до действия владельца. Вовлечение добровольно, без рассылок/членства. Код и ресурсы независимы от Krisp; отклонения ради безопасности/доступности и дефектов указаны в research/contracts. Применяются отдельные reviewer-owned security.md и ux.md. Проверка требований не объявляется приёмкой реализации.

## Implementation approach

1. Согласовать существующий summary_sharing с content_scope: summary_only по умолчанию для совместимости, full_meeting только явно. Версия/стабильная ссылка/отзыв общие. Защитить legacy writer от изменения современной ссылки без версии.
2. Один resolver действительности публичной ссылки под блокировкой встречи. Узкая полная проекция и дочерний playback route. Никаких owner sessions. Общий внутренний проигрыватель принимает только явное проверенное доказательство публичного grant и повторно его проверяет; обычный доступ пользователя неизменен.
3. Новая общая страница переиспользует рендер протокола и дизайн-токены GRAF; отдельный небольшой JS для tabs/search/copy/audio/timestamps/первого приглашения. Summary-only не содержит transcript/audio даже скрытыми. Вход/регистрация через cookie продолжения, самостоятельная встреча — собственное пространство.
4. Панель владельца сохраняет F286 отправку итогов, добавляет общий scope и существующие адресные grants/invitations, аудиторию пространства, список/роли/отзыв, вкладку экспорта. Использовать действующие API и обработчики без второй рассылки.
5. Строгий Swift-парсер deep link и один pending intent; существующая WKWebView/route policy. Разделить Dev/production schemes и починить сохранение полного допустимого маршрута при входе.

## Validation Plan

quickstart.md содержит точные группы pytest/node/Swift и живую матрицу. Privacy/range/revoke/version/legacy regression обязательны до приёмки. Только synthetic fixtures. До сборки df; минимум 80 GiB целевой запас, ниже 50 GiB тяжёлая сборка не начинается. Проверки GRAF только /Applications/GRAF Dev.app через dev-harness и чистый exact commit; временные build intermediates очищаются после проверки. Production меняется только после ворот выпуска. CI, Dev и production evidence отмечаются раздельно.

## Project Structure

- `apps/server/src/twobrain_rec_server/cabinet/{summary_sharing,access,egress,rendering}.py`: reuse управления ссылкой/прав/проигрывания/рендера.
- `apps/server/src/twobrain_rec_server/cabinet/public_sharing.py`: resolver и явная безопасная проекция, если отделение сокращает cabinet.py.
- `apps/server/src/twobrain_rec_server/api/{summary_sharing,cabinet}.py`: существующие owner/public endpoints.
- `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/{fragments,pages}/`: окно и общая страница.
- `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/`: существующие стили/обработчик и публичный JS.
- `apps/macos/RecApp/Sources/Cabinet/`, `App/TwoBrainRecApp.swift`: переход/маршрут/вход.
- `apps/macos/{Scripts,Installer/Scripts}/`: регистрация схемы.
- `apps/server/tests/{integration,contract,browser}/`, `apps/macos/Shared/Tests/`: предметные проверки.
- `specs/292-sharing-krisp-parity/`: требования/дизайн/проверки/задачи/отчёты; `changes/unreleased/`: русский фрагмент изменений.

## Complexity Tracking

Новых платформ, сервисов, библиотек, общих фабрик и дублированного хранилища нет. Отдельный public resolver нужен как граница авторизации, отдельный parser — как граница внешнего ввода.

## Уточнение реализации FR-026

Общая функция рендера существующего проигрывателя принимает только состояния воспроизведения/дорожек и готовые разрешённые дополнительные элементы. Владелец передаёт свои действия, публичный reader — только узкую проекцию без owner DTO. Существующие JS/CSS проигрывателя используются обеими страницами; публичный JS сохраняет только tabs/search/continuation и связь таймкода. Не создавать второй механизм дорожек/выбора спикеров. Контроль доступа к каждому запросу аудио сохраняется.


## Приёмочный R6 / T023

Согласовать fingerprint почтовой identity в существующем `auth/workspace_onboarding.py` с `auth_email_flow.py` и `provider_links.py`. Применить нормализацию только для email при проверке исходной identity и выпуске replacement fingerprint; OAuth subject, проверки membership/срока/device, блокировка/замена и RLS неизменны. Email требует verified identity; OAuth не получает нового требования verified. Новый тест в существующей workspace onboarding группе до исправления (hashed subject/email туда и обратно, wrong fingerprint/inactive identity/unverified email/inactive membership, OAuth roundtrip), затем PostgreSQL focused, canonical auth regressions и отдельный Dev grant/role/revoke. Никаких новых зависимостей/API/миграций. Полный high-risk-product lane сохраняется.
