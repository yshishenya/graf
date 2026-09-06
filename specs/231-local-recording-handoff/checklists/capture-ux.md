# Requirements Quality Checklist: Capture, custody and local-row UX

**Purpose**: Reviewer gate for high-risk capture, deletion and desktop UX requirements
**Created**: 2026-09-02
**Ownership**: `[x]` means reviewer approval of requirement quality, not implementation completion. `$speckit-implement` reads but does not modify these markers. Reviewed on 2026-09-06; see the decision and evidence below.

## Capture and privacy boundaries

- [x] CHK001 Are finite overshoot, non-finite input, wrong frame size and genuine AEC failure specified as distinct cases? [Completeness, Spec §FR-010–FR-012]
- [x] CHK002 Is the no-raw-microphone-fallback boundary explicit for every terminal capture path? [Coverage, Spec §FR-012]
- [x] CHK003 Are cleaned-prefix retention and automatic-upload exclusion consistent? [Consistency, Spec §FR-006, FR-012]

## Custody and deletion

- [x] CHK004 Is the allowed deletion target bounded to the recordings root and exact user-selected records? [Clarity, Spec §FR-013–FR-014]
- [x] CHK005 Does the specification distinguish local package identity from server meeting identity throughout handoff? [Consistency, Spec §FR-009]
- [x] CHK006 Are queue refresh and legacy misclassification requirements defined without requiring manual queue-file edits? [Coverage, Spec §FR-007–FR-008]

## UX, localization and accessibility

- [x] CHK007 Are readable UTF-8, icon parity, duration truth and local primary action each independently specified? [Completeness, Spec §FR-001–FR-005]
- [x] CHK008 Are pointer, keyboard and assistive-technology activation requirements present for the local primary action? [Coverage, Spec §US1/AC2, Edge Cases]
- [x] CHK009 Is behavior defined when playback is absent and while server truth has not yet appeared in the refreshed list? [Edge Case, Spec §Edge Cases]

## Acceptance quality

- [x] CHK010 Can the no-duplicate handoff result and AEC safety boundary be measured objectively? [Measurability, Spec §SC-003–SC-004]
- [x] CHK011 Are cleanup success and preservation of the known-good meeting both explicit? [Completeness, Spec §SC-005]

## Notes

- Reviewer should evaluate wording before implementation; implementation evidence belongs in tasks/quickstart, not in this checklist.
- Review evidence belongs in the PR and quickstart; this file stays reviewer-owned.

## Решение рецензента 2026-09-06

Рецензент — отдельный агент проверки выпуска F238, не автор производственного
изменения PR #6504. Проверены тексты spec.md, plan.md, контракта локальной строки,
quickstart.md и tasks.md. Одобрены 11/11 критериев **качества требований**:

| Критерии | Проверенное основание |
|---|---|
| CHK001 | FR-010–012 и US3/AC1–2 отдельно описывают конечный пик, NaN, размер кадра и отказ AEC. |
| CHK002 | FR-012 и US3/AC2 запрещают raw-mic fallback при терминальном отказе. |
| CHK003 | FR-006 и FR-012 сохраняют только очищенный префикс и исключают автоматическую отправку. |
| CHK004 | FR-013–014 и US4 ограничивают корень, явно выбранные записи и сохраняемый объект. |
| CHK005 | FR-009, US2 и раздел Handoff контракта разделяют локальную и серверную идентичность. |
| CHK006 | FR-007–008 требуют исправлять категорию при обновлении очереди; ручное редактирование файлов не требуется. |
| CHK007 | FR-001–005 независимо задают UTF-8, пиктограмму, доступное действие, файл и длительность. |
| CHK008 | US1/AC2 задаёт мышь/клавиатуру; Edge Cases и quickstart §2 явно включают Tab, Enter/Space и VoiceOver. |
| CHK009 | FR-004 задаёт отсутствие/нечитаемость playback, FR-009 и US2 — ожидание серверной строки. |
| CHK010 | SC-003 задаёт 1000 кадров и отклонение неверного входа; SC-004 — максимум одну строку. |
| CHK011 | SC-005 и FR-014 явно задают результат удаления и сохранность выбранной успешной записи. |

Это запоздалая проверка требований, она не восстанавливает доказательство
предварительного review и не утверждает, что сегодня повторены запись,
удаление, VoiceOver и весь путь F231. Для ограниченного изменения отображения
F238 применимы прежде всего CHK007–009 и неизменность границ CHK004–005.
Результат проверки реализации и границы convergence:
[F238-review-convergence.md](../F238-review-convergence.md).
