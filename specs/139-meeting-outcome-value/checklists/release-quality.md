# Release-quality Requirements Checklist: meeting-outcome-value

**Purpose**: Проверить полноту, ясность и измеримость требований к AI quality,
UX/CX, privacy, accessibility и release governance до task generation.
**Created**: 2026-08-04
**Feature**: [spec.md](../spec.md)

**Depth**: formal high-risk release gate. **Audience**: author, PR reviewer,
operator. Этот checklist проверяет качество требований, а не реализацию.

## Product outcome and scope

- [x] CHK001 Определён ли главный пользовательский результат через конкретные вопросы и 30-секундный критерий, а не через абстрактное «хорошее summary»? [Clarity, Spec §Product Outcome, SC-003]
- [x] CHK002 Описан ли весь primary journey от usable transcript до accepted/shareable result с alternate, exception и recovery paths? [Completeness, Spec §US1–US8]
- [x] CHK003 Согласован ли scope compact IA с запретом на task hub, chat, новый framework и competitor copying? [Consistency, Spec §FR-021, Out of Scope]
- [x] CHK004 Зафиксировано ли, какие существующие capture/retention/deletion boundaries не меняются? [Completeness, Spec §FR-022, Assumptions]

## Automatic generation lifecycle

- [x] CHK005 Определены ли точный trigger, policy gate, default template и durable identity automatic candidate? [Clarity, Spec §FR-001–FR-002; Contract §1]
- [x] CHK006 Различены ли automatic generation, acceptance и sharing так, чтобы ни одно понятие не допускало silent overwrite? [Consistency, Spec §FR-003, US7]
- [x] CHK007 Описаны ли idempotency/reload/restart/second-device и retry boundaries с измеримым «не более одного publishable call»? [Coverage, Spec §SC-002]
- [x] CHK008 Определено ли поведение при disabled policy, invalid default, unusable transcript, stale source и dependency outage без блокировки текущей ценности? [Coverage, Spec §US6, Edge Cases; Contract §1]
- [x] CHK009 Установлено ли performance-boundary, что processing не ждёт remote AI/Temporal network I/O, и указан ли reconciliation target? [Clarity, Plan §Performance Goals]

## Prompt semantics and evidence

- [x] CHK010 Даны ли однозначные определения decision, action, proposal, question, risk и follow-up? [Clarity, Spec §FR-005; Contract §2]
- [x] CHK011 Определены ли correction, contradiction, deduplication, filler и compactness rules для разных detail levels? [Completeness, Spec §FR-006, FR-011; Contract §2]
- [x] CHK012 Определён ли fail-closed контракт minimum/maximum refs, exact pinned IDs/sequences и duplicate rejection? [Clarity, Spec §FR-007; Contract §3]
- [x] CHK013 Разделены ли structural runtime validation, semantic entailment eval и human acceptance без ложного обещания локальной semantic verification? [Consistency, Contract §3]
- [x] CHK014 Зафиксировано ли, что owner/due допустимы только у action и только при прямом evidence, включая unknown/generic speaker и relative date cases? [Coverage, Spec §FR-008–FR-009, US4]
- [x] CHK015 Описана ли untrusted-data boundary для transcript/custom template, indirect injection, role/schema/link и secret-disclosure attempts? [Completeness, Spec §FR-010, Edge Cases]
- [x] CHK016 Определено ли поведение у long-context boundary без hidden truncation и с фактами в начале/середине/конце? [Coverage, Spec §SC-007, Edge Cases]

## Candidate, accepted and shared UX

- [x] CHK017 Задан ли единый локализованный порядок primary/secondary sections для candidate, accepted и разрешённого shared projection? [Consistency, Spec §FR-012, FR-020]
- [x] CHK018 Определено ли, какие owner/due/source данные видны до принятия и какие два смысловых исхода доступны владельцу? [Completeness, Spec §FR-012–FR-013; Contract §4]
- [x] CHK019 Зафиксировано ли, что unaccepted candidate исключён из viewer/share/export во всех lifecycle states? [Coverage, Spec §FR-014, SC-009]
- [x] CHK020 Определено ли различие интерактивного source destination и bounded non-interactive source при no transcript/player/access? [Clarity, Spec §FR-023; Contract §5]
- [x] CHK021 Указаны ли tab/hash/seek/focus/assistive-announcement outcomes успешного evidence jump? [Measurability, Spec §US8, FR-023]
- [x] CHK022 Описан ли summary-only browser entry как product HTML с тем же read-only IA, а не JSON/raw keys? [Completeness, Spec §FR-020, US8]
- [x] CHK023 Определено ли одно aggregate non-ready state и запрещён ли повтор одного reason по трём primary sections? [Clarity, Spec §FR-024, SC-012]
- [x] CHK024 Различает ли requirement meeting-list readiness расшифровки и accepted outcomes и исключает ли optimistic unknown=`Готово`? [Clarity, Spec §FR-025]

## Accessibility and responsive behavior

- [x] CHK025 Определены ли keyboard, focus, heading outline и disabled-action explanation требования для всех новых/затронутых controls? [Coverage, Spec §FR-026]
- [x] CHK026 Задан ли конкретный mobile viewport и measurable no-overflow criterion? [Measurability, Spec §SC-008, SC-012]
- [x] CHK027 Согласованы ли web, embedded, owner, full-viewer и summary-only semantics без требования показывать недоступный content? [Consistency, Spec §FR-020, FR-023]

## Eval and prompt governance

- [x] CHK028 Перечислены ли независимые eval dimensions вместо одного aggregate quality score? [Completeness, Spec §FR-016]
- [x] CHK029 Определены ли critical hard failures, которые нельзя скрыть средним score? [Clarity, Spec §FR-017, SC-004, SC-006]
- [x] CHK030 Квантифицированы ли action precision/recall, owner/due restraint, must-unit coverage и long-context thresholds? [Measurability, Spec §SC-005, SC-007]
- [x] CHK031 Описаны ли dataset split/version/hash, private held-out, judge calibration и operator approval requirements? [Completeness, Spec §FR-018; Contract §7]
- [x] CHK032 Различены ли prompt candidate creation/sync и production label promotion, включая expected source и rollback target? [Consistency, Research §6; Contract §7]
- [x] CHK033 Ограничен ли committed eval evidence metadata-only полями без transcript/output/free feedback? [Clarity, Spec §FR-019]

## Privacy, failure and release

- [x] CHK034 Покрыты ли deletion/access races, stale/expired candidate и ambiguous provider outcome без content disclosure или implicit retry? [Coverage, Spec §Edge Cases, FR-015]
- [x] CHK035 Согласованы ли exact accepted pointer, plaintext observability policy и owner-only candidate с constitution? [Consistency, Plan §Constitution Check]
- [x] CHK036 Разделены ли implementation validation, prompt promotion, production deploy и public Developer ID package как самостоятельные gates? [Clarity, Plan §Release Gate; Quickstart §Repository and release gates]
- [x] CHK037 Определена ли before/after Browser state matrix так, чтобы screenshots дополнялись runtime/focus checks и не содержали meeting content? [Completeness, Quickstart §Browser evidence]

## Notes

- 37/37 requirement-quality checks passed after Phase 0/1 refinement.
- Implementation behavior будет проверяться tasks/tests/Browser evidence, а не
  этим checklist.
