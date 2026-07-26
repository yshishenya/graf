# Security Checklist: Developer ID как единственный публичный macOS-релиз

**Purpose**: Проверить качество требований к цепочке доверия, signing lineage,
notarization и секретам до реализации.
**Created**: 2026-07-26
**Feature**: [spec.md](../spec.md)

## Цепочка подписи и доверия

- [x] CHK001 Определено ли, что public app и package используют именно Developer ID Application/Installer? [Completeness, Spec §FR-001]
- [x] CHK002 Однозначно ли отделены notarization, stapling и Gatekeeper как отдельные обязательные проверки? [Clarity, Spec §FR-002]
- [x] CHK003 Явно ли отклонены ad-hoc, local/self-signed и owner-only identities до публикации? [Consistency, Spec §FR-003]
- [x] CHK004 Определено ли, что обычный Sparkle update не может менять signing kind или team lineage? [Completeness, Spec §FR-005]
- [x] CHK005 Есть ли измеримый negative outcome для отказа до изменения public files/appcast? [Measurability, Spec §SC-002]

## Переход и злоупотребление режимами

- [x] CHK006 Отделён ли manual migration bootstrap от ordinary in-app update? [Clarity, Spec §FR-004]
- [x] CHK007 Указано ли, что migration bootstrap принимает legacy predecessor только для manual `.pkg`? [Completeness, Spec §FR-004]
- [x] CHK008 Указано ли, что migration bootstrap не публикует appcast entry и не заменяет live feed? [Edge Case, Spec §FR-004]
- [x] CHK009 Описан ли отказ при несовпадающих bundle identity, feed URL, Sparkle key или неполной конфигурации? [Coverage, Spec §Edge Cases]
- [x] CHK010 Разделены ли Apple code-signing secrets и Sparkle Ed25519 custody без требования сохранять private material в репозитории? [Security, Spec §FR-009]

## Evidence и откат

- [x] CHK011 Ограничено ли release evidence метаданными, checksum и status ID без key/password/signed URL? [Security, Spec §FR-009]
- [x] CHK012 Определено ли сохранение старого appcast и rollback assets до успешной проверки кандидата? [Recovery, Spec §FR-008]
- [x] CHK013 Сохранён ли запрет переписывать исторические receipts так, будто старые artifacts были notarized? [Consistency, Spec §Assumptions]
