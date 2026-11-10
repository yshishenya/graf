# Security Checklist: Сквозное укрепление интерфейса GRAF

**Purpose**: Проверить требования к приватности смены аккаунта, сессиям, логам, диагностике и публикации релиза.
**Created**: 2026-11-10
**Feature**: [spec.md](../spec.md)

**Note**: Reviewer-owned requirements-quality artifact.
**Marker Semantics**: `[x]` means the requirements-quality criterion is satisfied; it does not mean implementation is complete.

## Account & Session Privacy

- [x] CHK001 Определено ли, что при смене аккаунта старые встреча, название, напоминание и плеер исчезают? [Completeness, Spec §FR-006]
- [x] CHK002 Определено ли, что сброс выполняется до сетевого обновления новых данных? [Clarity, Spec §Interface Contract]
- [x] CHK003 Определено ли, что in-flight ответы старого сеанса игнорируются? [Completeness, Spec §Interface Contract]
- [x] CHK004 Определено ли, что web bridges и cookies не переносят состояние между аккаунтами? [Consistency, Spec §FR-006]
- [x] CHK005 Определено ли, что локальные записи не меняют владельца без явного правила? [Clarity, Spec §Interface Contract]

## Sensitive Data In UI & Logs

- [x] CHK006 Определено ли, какие данные запрещены в обычном UI и логах? [Completeness, Spec §FR-002, §FR-012]
- [x] CHK007 Уточнено ли, что пути, токены, sessionId и внутренние коды не попадают в сообщения? [Clarity, Spec §FR-002]
- [x] CHK008 Определено ли, что редакция логов не слабее диагностического redactor? [Consistency, Spec §FR-012]
- [x] CHK009 Определено ли, что скриншоты и evidence не содержат приватных встреч? [Completeness, Spec §Assumptions]
- [x] CHK010 Определено ли, что support-сводка остаётся metadata-only? [Consistency, Constitution §III]

## Authentication Boundaries

- [x] CHK011 Определено ли, что смена аккаунта не обходит серверную авторизацию? [Consistency, Spec §FR-020]
- [x] CHK012 Определено ли, что кабинет не может открыть запрещённый маршрут после сброса? [Completeness, Spec §FR-006]
- [x] CHK013 Определено ли, что локальный режим не получает доступ к production-аккаунту? [Consistency, Spec §Assumptions]
- [x] CHK014 Определено ли, что поддержка входа не теряет attribution и не открывает чужой workspace? [Completeness, Spec §FR-020]
- [x] CHK015 Определено ли, что удаление и диагностика не расширяют права? [Consistency, Constitution §IV]

## Release Trust

- [x] CHK016 Определено ли, что публикация только Developer ID? [Completeness, Spec §FR-019]
- [x] CHK017 Определены ли notarization, staple, Gatekeeper и Sparkle gates? [Completeness, Spec §Release Contract]
- [x] CHK018 Определено ли, что non-notarized build не публикуется? [Consistency, Constitution §V]
- [x] CHK019 Определено ли, что appcast и ZIP проверяются после публикации? [Completeness, Spec §SC-007]
- [x] CHK020 Определён ли rollback при неудачной нотаризации/Sparkle? [Coverage, Spec §Release Contract]

## Failure & Abuse

- [x] CHK021 Покрыт ли сценарий смены аккаунта во время открытой встречи и напоминания? [Coverage, Spec §Edge Cases]
- [x] CHK022 Покрыт ли сценарий нескольких одновременных Stop? [Coverage, Spec §Edge Cases]
- [x] CHK023 Покрыт ли сценарий недоступного кабинета при открытии настроек? [Coverage, Spec §Edge Cases]
- [x] CHK024 Покрыт ли сценарий повреждённой/удаляемой записи? [Coverage, Spec §Edge Cases]
- [x] CHK025 Определено ли, что analytics scaffold не включается случайно? [Consistency, Spec §Assumptions]

## Notes

- Отмечать `[x]` только после проверки требований, а не реализации.
- Пункты без подтверждения оставлять `[ ]` с причиной в отчёте ревью.
