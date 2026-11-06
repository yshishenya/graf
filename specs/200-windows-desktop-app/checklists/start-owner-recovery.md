# Start-owner recovery Checklist: Windows desktop GRAF

**Purpose**: качество требований исходной принадлежности, ACK и восстановления T116.
**Created**: 2026-10-16
**Feature**: [spec.md](../spec.md), Session 2026-10-16; [plan.md](../plan.md), §T116: исходный владелец до audio admission.
**Review Ownership**: reviewer-owned; отметки изменяет только независимый reviewer.
**Marker Semantics**: `[x]` означает качество требований, не выполненную реализацию.

## Полнота и ясность

- [x] CHK001 Определены ли confirmed owner, proven signed-out и unresolved auth без превращения network/bootstrap failure в no-login? [Completeness, Spec FR-012/013/014 и Session 2026-10-16; Plan §Носитель и начало]
- [x] CHK002 Заданы ли единственный допустимый создатель Start marker, свежая непереиспользуемая identity и запрет backfill marker из старых missing fields/row? [Clarity, Plan §Носитель и начало; Contract §Start-owner/recovery]
- [x] CHK003 Однозначны ли encrypted carrier, full BOTH commit/readback/adoption и граница до factory/prepared/первого блока без нового schema или обещания durable FileId? [Consistency, Plan §Носитель и начало и §Finalizer и restart; Data model §durable Start-owner]

## Действия и восстановление

- [x] CHK004 Определены ли worker-side action fences preparing/active/partial reservation независимо от скрытия строки в UI? [Coverage, Plan §Носитель и начало; Contract §Start-owner/recovery]
- [x] CHK005 Заданы ли exact-row update/restart вместо повторного enqueue, immutable owner и запрет продвижения при server/deletion/alias conflict? [Consistency, Plan §Finalizer и restart; Spec FR-013/022]
- [x] CHK006 Различены ли known no-login и unknown/legacy в display/manual claim/HTTP без общего разрешения всей quarantine или назначения текущего аккаунта после restart? [Clarity, Plan §Finalizer и restart; Desktop contract §принадлежность локальной записи]
- [x] CHK007 Описаны ли complete480-prefix/zero/partial/key/IO/quota failure и сохранение неизвестных старых пакетов без normal claim, plaintext fallback и автоматической достройки/удаления? [Coverage, Plan §Finalizer и restart; Spec FR-012; Custody contract §4–7]

## Удаление, ресурсы и приёмка

- [x] CHK008 Согласованы ли positive BOTH short intent, exact Start-row retirement/commit/adoption и прежний no-queue-alias physical discard без стирания отдельных deletion operations? [Consistency, Plan §Short и deletion; Custody contract §Start-owner/recovery]
- [x] CHK009 Достаточно ли определены publication/readback/adoption/birth/seal/claim/short crash cuts, stale epoch, lost poll и удержание ownership при ambiguous outcome? [Measurability, Quickstart §Start-owner и аварийное восстановление; Plan §Реализация и доказательства]
- [x] CHK010 Сохранены ли offline Record/видимый Stop, memory/pin/job limits и отдельные synthetic/native/installed/hardware/release доказательства в рамках existing T116 без нового сервиса/публичного READY? [Consistency, Spec FR-012/015 и SC-003/005/008; Plan §Реализация и доказательства]

## Notes

Требования оцениваются до кода. Unsupported пункты остаются `[ ]` с причиной
в независимом отчёте; основной исполнитель не меняет отметки.

### Независимая проверка Round434 — 2026-10-16

10 checked / 0 unchecked. H2 закрыт независимым перечитыванием quickstart §Start-owner,
пункт4: только актуальные invalidation отзывают authority и дают unknown;
stale document/nonce/Source callback игнорируется без изменения более нового
auth/ownership state. Оба исхода проверяются раздельно.
Доказательства по всем десяти пунктам, scoped analyze и текущие нормативные SHA:
[review-2026-10-16-start-owner-requirements.md](review-2026-10-16-start-owner-requirements.md).
Это качество требований, не source/runtime GO и не выполнение T116.
