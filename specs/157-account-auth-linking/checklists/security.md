# Security Requirements Checklist: Связанные способы входа

**Purpose**: Проверить полноту и однозначность требований к доказательству
владения, merge, сессиям, tenant boundaries и audit.
**Created**: 2026-08-16
**Feature**: [spec.md](../spec.md)

## Proof and account selection

- [x] CHK001 Требования явно разделяют доказательство email, доказательство OAuth и простое совпадение email [Completeness, Spec §FR-002–FR-005]
- [x] CHK002 Запрещён выбор survivor по времени создания, случайности или одному normalized email [Clarity, Spec §Edge Cases, FR-003–FR-006]
- [x] CHK003 Для auto-link пустого duplicate и для merge аккаунтов с данными определены разные уровни подтверждения [Consistency, Spec §FR-006–FR-007]
- [x] CHK004 Требования описывают single-use, expiry, replay и concurrent-attempt поведение intent [Coverage, Spec §FR-006, FR-015]

## Data safety and authorization boundaries

- [x] CHK005 Для встреч, записей, processing, artifacts, workspace, roles, sharing, billing, calendar и deletion задано отдельное правило сохранения или блокировки [Completeness, Spec §Merge Policy]
- [x] CHK006 Явно запрещено молчаливое повышение роли, смешивание workspaces и суммирование billing state [Clarity, Spec §FR-008–FR-009]
- [x] CHK007 Отмена, ошибка, expired intent, stale preview и блокирующий конфликт определены как zero-mutation outcomes [Coverage, Spec §FR-006, Merge Policy]
- [x] CHK008 Определены сохранение стабильных ID, FK lineage и non-destructive archival source account [Traceability, Spec §FR-008, Merge Policy]

## Secrets, sessions and audit

- [x] CHK009 Требования запрещают хранение или раскрытие raw codes, tokens, provider secrets, transcripts и meeting content в evidence/UI/audit [Completeness, Spec §FR-014–FR-015, SC-007]
- [x] CHK010 Revocation текущих/старых sessions, device trust и повторная авторизация устройства описаны после успешного merge [Coverage, Spec §Merge Policy]
- [x] CHK011 CSRF/state/nonce, RLS, rate limits и provider policy названы обязательными границами без ослабления [Consistency, Spec §FR-015–FR-016]
- [x] CHK012 Требования к metadata-only audit различают success, reject, cancel, block, failure и replay [Measurability, Spec §FR-014, contracts/merge.md]

## Notes

- Все security items проходят на уровне требований; implementation validation
  остаётся в `quickstart.md` и задачах.
