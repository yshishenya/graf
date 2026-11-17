# Infra And Evidence Requirements Checklist: MVP Live Owner Journey And UI Proof

**Purpose**: Validate production evidence, timing, and release requirement quality before implementation
**Created**: 2026-06-25
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Are release tag, deployed SHA, production health, and installed app version all included in the proof model? [Completeness, Owner Journey Contract §Required P1 Gates]
- [x] CHK002 Are owner journey gates specified with pass/fail/blocked/unproven/out-of-scope states? [Completeness, Owner Journey Contract §Required P1 Gates]
- [x] CHK003 Are stored outcome category states and counts included as a P1 production proof gate? [Completeness, Spec §FR-004]
- [x] CHK004 Is representative timing evidence specified with audio duration, queue/wait, workflow, provider, finalize-to-review, and result? [Completeness, Timing Contract §Required Fields]

## Requirement Clarity

- [x] CHK005 Is the 180-second-per-hour target stated without allowing extrapolation from short recordings? [Clarity, Spec §FR-005, Timing Contract §Target Rule]
- [x] CHK006 Are `pilot_blocked`, `internal_pilot_candidate`, `user_rollout_ready`, and `production_ready` claim boundaries explicit? [Clarity, Spec §SC-007, Owner Journey Contract §Claim Rules]

## Scenario Coverage

- [x] CHK007 Are no-current-candidate and no-long-timing-candidate cases covered as valid blocked/unproven outcomes? [Coverage, Spec §User Story 2]
- [x] CHK008 Are production health green but owner review unavailable cases covered? [Coverage, Spec §Edge Cases]
- [x] CHK009 Are local fixture/synthetic evidence boundaries separated from production proof? [Consistency, Spec §FR-003]

## Acceptance Criteria Quality

- [x] CHK010 Can local CI, deploy dry-run, execute deploy, and production health checks be objectively tied to release readiness? [Acceptance Criteria, Quickstart §8-10]

## Независимое ревью 2026-11-17 — F052/T020

Исполнитель: /root/f140_account_db_budget_research; основа 72079434d3fa151725c16ed6044da175c8955e51. CHK010 не подтверждён: quickstart §§8–10 и plan с bare ci-local.sh не отражают действующие required GitHub governance-fast/macos-pr/pr-metadata на exact SHA/base, frozen candidate и отдельный authoritative release-full/decision gate. Health или dry-run сами по себе выпуск не разрешают. Формулировки пунктов не изменены.

Итог: 9 отмечено, 1 не отмечен. Это качество требований, а не приёмка выпуска/развёртывания; допуск к реализации: STOP.

## T020 — уточнённые требования к проверке метаданных

Новые пункты сформированы владельцем требований и оставлены неподтверждёнными.
Их отметки принадлежат независимому проверяющему; это качество требований,
не выполненная реализация или фактическая приёмка.

- [x] CHK011 Определены ли типы и источники полей, все состояния доступа/встречи/категорий, порядок отрицательных результатов, общий результат и код завершения без неявного преобразования значений? [Completeness, Spec FR-016–019; Owner contract Type and source rules / Decision order]
- [x] CHK012 Определены ли счётчики расшифровки, полос/интервалов/переходов по времени и восьми категорий, отличие нуля от отсутствия данных и допустимые пустые/протокольные результаты? [Clarity, Spec FR-018; Owner contract Outcome state matrix]
- [x] CHK013 Определены ли только GET, проверка входов и границы Cookie/redirect, допустимый безопасный вывод и изолированные отрицательные/положительные проверки без сети и настоящих данных? [Coverage, Spec FR-017/019; Owner contract Inputs and safety / Required offline regressions]
- [x] CHK014 Сохранены ли исходные живые критерии T019/T020 и явное отличие API metadata pass от пути свежей записи, видимого UI, выпуска и развёртывания? [Consistency, Spec US1/SC-001/003/004/FR-016; Owner contract Claim Rules; Tasks T020]

## Повторное независимое ревью после уточнений — 2026-11-17

Исполнитель: /root/f140_account_db_budget_research; HEAD72079434d3fa151725c16ed6044da175c8955e51. Прежние STOP-примечания выше относятся к старому снимку.

CHK010 подтверждён актуальными quickstart8–10 и plan continuation: exact-SHA/base required GitHub, отдельные immutable candidate/release-full/decision/CD ворота и ограниченность health/local CI явны. CHK011: owner contract61–78/89–145 определяет типы, enums, приоритеты, общий результат и exit; сверено с реальными схемами API. CHK012: contract80–109 определяет счётчики, честные нули и точное исключение protocol-risks; соответствует stored_outcome_truth_state3255–3304. CHK013: contract44–59/147–156 определяет HTTPS origin/UUID/timeout, GET-only, запрет redirect Cookie и безопасный вывод/изолированные регрессии. CHK014: spec US1/SC001/003/004, contract139–145 и tasks T019/T020 сохраняют отдельную живую приёмку. Положительная API metadata не доказывает UI, свежесть или полный путь.

Итог infra: 14 отмечено / 0 не отмечено. Общий набор49/1 остаётся STOP из-за UX CHK010; код, тесты и live acceptance этим ревью не выполнены.

## Независимое ревью второй правки требований — 2026-11-17

Исполнитель /root/f140_account_db_budget_research; HEAD 72079434d3fa151725c16ed6044da175c8955e51. Все 14 пунктов заново проверены: типы/enums и реальный API источник, счётчики/честные нули, bounded protocol risks, приоритет schema → candidate mismatch → access → state → availability, health/aggregate/exit и privacy определены. Контракт требует offline cases missing/null/non-string/invalid/different UUID и normalized equality. Quickstart/plan требуют отдельное focused evidence на фактической версии; общий PR check не доказывает автоматический запуск evidence-directory unittest. Original T019/T020, UI/Dev/timing и отдельные exact-SHA PR/release/deploy ворота сохранены.

Итог infra 14/0; общий набор 50/0, PASS только качества требований текущего снимка. Реализация probe пока не выполнена; old STOP notes сохраняют исторический смысл. Root analyze/issue sync и последующие доказательства остаются отдельными воротами.
