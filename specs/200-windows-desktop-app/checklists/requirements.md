# Requirements Checklist: Windows desktop-приложение GRAF

**Purpose**: Проверить, что спецификация Feature 200 полна, измерима и
готова к реализации, не проверяя конкретный код.
**Created**: 2026-08-23
**Feature**: [spec.md](../spec.md)

## Полнота и трассируемость

- [X] CHK001 Для каждого из FR-001–FR-022 указано наблюдаемое пользовательское или системное требование и есть связь с задачей реализации. [Completeness, Spec §Requirements]
- [X] CHK002 Для каждого из SC-001–SC-010 определены источник evidence, измеримый порог и задача, которая создаёт нужный proof. [Measurability, Spec §Success Criteria]
- [X] CHK003 Все пять user stories имеют независимый тест, acceptance scenarios и явную границу зависимости от других историй. [Traceability, Spec §User Scenarios & Testing]
- [X] CHK004 Описаны обе границы владения: что делает native Windows host и что остаётся серверному кабинету. [Completeness, Spec §FR-002–FR-004]
- [X] CHK005 Указаны требования для normal, degraded, failed, blocked и recovery состояний, а не только для успешной записи. [Coverage, Spec §Edge Cases]

## Ясность и измеримость

- [X] CHK006 Термин «идентичен macOS» раскрыт через parity matrix, пользовательские смыслы состояний, copy, accessibility и ownership, а не трактуется как одинаковый toolkit. [Clarity, Spec §FR-002, §SC-002]
- [X] CHK007 Формулировка «approved route» связана с конкретным origin, route kinds и правилами для redirect, auth и внешнего браузера. [Clarity, Spec §FR-003, §FR-005]
- [X] CHK008 Определены границы слов «normal», «trusted segment», «degraded» и «protected-audio limitation», включая допустимое содержимое manifest. [Clarity, Spec §FR-010–FR-017]
- [X] CHK009 Все временные пороги, размеры очередей, лимиты bridge payload и критерии drift либо заданы в требованиях, либо имеют ссылку на утверждённый contract. [Measurability, Spec §FR-009, §FR-018, §SC-001, §SC-003]
- [X] CHK010 Сформулировано, что считается готовностью Record и какие именно prerequisites блокируют старт. [Clarity, Spec §FR-004, §FR-007–FR-010]

## Согласованность

- [X] CHK011 Требования FR-007–FR-010 согласованы с `windows-desktop-contract.md` по loopback, microphone, AEC3 order, bounded queue и fail-closed политике. [Consistency, Spec §FR-007–FR-010]
- [X] CHK012 FR-011–FR-014 используют те же имена `v5`, `desktop-upload-queue.v2`, artifact roles и server truth, что и data model. [Consistency, Spec §FR-011–FR-014]
- [X] CHK013 WebView bridge не получает полномочий, которые запрещены в desktop contract, а события capture не трактуются как подтверждение сохранения или upload. [Conflict, Spec §FR-004–FR-006]
- [X] CHK014 Требования автоматической записи не ослабляют требования явного opt-in, verified identity, countdown, indicator и Stop. [Consistency, Spec §FR-016]
- [X] CHK015 Out of Scope не противоречит архитектуре: process loopback, Stereo Mix, virtual driver, exclusive mode, service/elevation и отдельная Windows web UI явно исключены. [Consistency, Spec §Out of Scope]

## Сценарии и предположения

- [X] CHK016 Для отсутствия WebView2, сети, auth-сессии, endpoint, microphone permission и диска определены отдельные safe state и recovery action. [Coverage, Spec §Edge Cases]
- [X] CHK017 Для sleep/wake, endpoint invalidation, audio-service restart, clock discontinuity и overflow указано, когда trusted prefix можно сохранить и когда normal package запрещён. [Recovery, Spec §FR-017]
- [X] CHK018 Для Windows N/Media Feature Pack определены поддерживаемая линия, readiness result и правило запрета ложного normal package без playback artifact. [Dependency, Spec §Edge Cases]
- [X] CHK019 Предположения о стабильности существующих cabinet routes, upload API, v5 manifest и deletion lifecycle выделены и имеют owner/условие пересмотра. [Assumption, Spec §Assumptions]
- [X] CHK020 Граница evidence явно запрещает raw audio, transcript, credentials, cookies, signed URLs, private meeting content и live private paths во всех артефактах Feature 200. [Security, Spec §FR-012, §FR-021]

## Решение перед реализацией

- [X] CHK021 Не осталось требований с vague словами «быстро», «безопасно», «идентично» или «надёжно», для которых отсутствует порог или наблюдаемое условие. [Ambiguity]
- [X] CHK022 Каждая будущая серверная или shared-contract правка выделена в отдельную approved slice и не скрыта внутри Windows-only задачи. [Dependency, Spec §Assumptions]
