# Implementation Plan: Единый интерфейс настроек

## Summary
Общая центрированная колонка и визуальная система настроек; исправление подтверждённых сообщений результатов; понятная нативная автозапись и проверенная очистка.

## Technical Context
Python/FastAPI/Jinja, существующий cabinet.css/cabinet.js; SwiftUI/AppKit, Swift Package. Новых зависимостей/миграций нет. Risk lane: **high-risk-product** (reference fidelity, accessibility, auth result presentation). Base SHA: `107e7e692b896863f70ba632a101469d6f80e29a`.

## Constitution Check
До и после проектирования PASS: system-audio-first, consent/stop, client-owned three-state recording, server auth/CSRF/ownership, deletion truth и независимая реализация сохраняются. Блокирующих уточнений нет (spec Clarifications). Требуется независимая проверка ux-security checklist перед реализацией. Commit/deploy не разрешены этим этапом; fast local — диагностическая проверка, GitHub exact-SHA gate нужен перед PR/merge, release-full нужен только перед выпуском.

## Structure and implementation
1. CSS: нормализовать inner columns settings/calendar; оплата сохраняет ширину; общий шрифт scope badges, секции/списки/формы, адаптивные строки. Удалить доказанно мёртвые selectors/дубли, не менять глобальную meeting workspace.
2. Templates: короткие вводные, точные подписи, прямой download; сохранить имена форм, действия, CSRF, dialog/data hooks и роли.
3. Routes/rendering: восстановить передачу profile/account_close в обеих оболочках, классифицировать outcome и reauth правдиво, убрать только лишние context keys. Проверить соседние account routes.
4. Native: согласовать окно и content размер, объяснить правила/сохранение/разные значения; сохранить bindings/store и capture behavior. Удалить неиспользуемую max-width константу с её tautological assertion.
5. Проверить реальные synthetic renders через Computer Use, замеры ширин и Python/Swift suites; независимый correctness/Ponytail review и convergence.

## Legacy Impact
remove: только отсутствие потребителей/неработающие CSS declarations/неиспользуемая константа. Миграции autoRecordTargetIds, deny routes, account aliases и старые protocol boundaries вне очистки: это активные compatibility/security contracts, не бесхозный код.

## Validation
См. quickstart.md. Требуется сохранение/ошибка/reauth обоих каналов, synthetic long/empty states, 320–1440px и 200% масштаб, light/dark, keyboard, native window. Снимки личных данных вне git. Общий dev runtime не перезапускать.
