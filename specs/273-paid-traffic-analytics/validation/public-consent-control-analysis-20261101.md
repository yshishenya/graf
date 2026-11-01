# T106 — анализ индивидуального серверного выбора, 01.11.2026

Область: текущий public-consent-control срез существующей T106/#7696,
high-risk-product. Scoped reread F273 разрешён владельцем; прежние четыре
базовых документа подтверждены неизменными хешами. Это не анализ/приёмка
всех прежних открытых частей F273.

Результат read-only analyze после текущего tasks: CRITICAL0/HIGH0/MEDIUM0,
blocking clarification0, ambiguity0, duplication0, unmapped tasks0.
12 применимых FR и SC-004 покрыты одной существующей T106, новых IDs нет.

| Требования | Покрытие T106 | Проверяемое условие |
| --- | --- | --- |
| FR-001/002/003/006 | этапы1–4,6 | явный revoke→CAS grant, read не разрешает, stale epoch запрещён |
| FR-004/059 | этапы3/4/6 | pending/доступная повторная кнопка, отказ при неизвестности |
| FR-007/008 | этапы2/3/6 | RLS, control ID не передаётся receiver/уровням1/2 |
| FR-048/049 | этапы1/3/5/6 | lock до завершения send, отзыв после commit, named case |
| FR-050/051 | этапы2/5/6 | until_decision, полный dump/inventory, все epoch меняются при restore |
| SC-004 | этапы1/4/6 | причинный PG+два процесса, настоящий CookieConsent/повторный визит |

Противоречий принципам конституции не найдено: явный выбор, строгие поля,
прежний self-hosted receiver/final gate, полный lifecycle, независимое ревью.
Checklist PASS6/0 — только требования; общий T106, T113, SDK, runtime/T0 и
операционная приёмка открыты. Этапы зависимы, параллельной записи кода нет.
setup/check-prerequisites текущей версии не поддерживает --require-spec;
использован --require-tasks --include-tasks, наличие spec проверено чтением.
До кода: mandatory issue-canon ensure → sync существующего владельца → validate.

## Контрольные суммы после анализа

- `spec.md`: `97663e9c246c20d1f95fef2a85968638deecc4550c62f990089c05f3a9f91925`
- `plan.md`: `c1233f0fa723af1cc835ce57390e9ae10cfe06553c8027e5392171f494834a30`
- `tasks.md`: `022da0262417652e77cdb3f65a92b897ab7d617b472c818ca796db6032eb50ed`
- `data-model.md`: `a167c60afd0bdc85d05b6243c43e6ad7708d2c9d54703ff8a37b3b112f8b3893`
- `research.md`: `973bc558431f4522f325f03ab5d54200a5dacdaf57377183606b9246e1f52069`
- `quickstart.md`: `9ebf2119dd16e932331b464ab722ed7b71808713b0d1dd67ac22f7f44902f4a0`
- `contracts/public-consent-control.md`: `2bb000b982db96230c75d97037d85e91a3dd02ad7a24f5d892e42b08304e8f3e`
- `checklists/public-consent-control.md`: `c40a0091d8180227fcce932a8226f249bd288d6509b21edb25a0fa2317829c48`
