# V8 Remaining Screens Deep Pass

Date: 2026-06-15
Feature: `030-mvp-experience-design-system`
Figma page: `030 MVP Experience v8 - Clean RU`
Scope: `V8 07` through `V8 14`

## Purpose

This pass continues the Krisp-aligned V8 review after the first-path correction
queue for `V8 01` through `V8 06`. It focuses on the remaining value surfaces:
transcript review, speaker assignment, settings, web meeting list, web meeting
detail, share/export/delete, light-theme proof, and component QA rules.

The pass checks both visual mechanics and product IA:

- controls use stable sizes and do not drift between neighboring actions;
- visible copy is Russian and not implementation-facing;
- text does not overlap or clip inside the frame;
- each screen contains the product objects required for its job;
- web/list/detail states follow the same meeting-centric model as the desktop
  cabinet;
- governance copy stays truthful about what 2brain Rec can and cannot erase.

## Initial Audit Findings

The first Figma API audit of `V8 07` through `V8 14` found these issues:

- `V8 10 - Веб-кабинет: встречи и фильтры`
  - browser chrome still showed `rec.2brain.dev / встречи`;
  - the upcoming meeting copy overlapped the policy chip;
  - table headers `Длит.` and `Источник` overlapped;
  - one upload row still used `client-call.mp4` as the primary meeting title;
  - a processing row action still said `Статус`;
  - bottom filter chips overlapped.
- `V8 11 - Веб-детали встречи и транскрипт`
  - browser chrome still showed `rec.2brain.dev / встреча`;
  - playback time overlapped the `2 дорожки` source chip.
- `V8 12 - Поделиться, экспорт, удаление`
  - browser chrome still showed `rec.2brain.dev / доступ`;
  - export row format labels overlapped `Скачать` buttons;
  - deletion truth did not explicitly mention external copies or outside-control
    limits.
- `V8 13 - Светлая тема: проверка экрана`
  - one light-theme row still used `client-call.mp4` as the primary title;
  - one row action still used vague `Статус`.
- `V8 14 - Правила интерфейса и QA`
  - ownership boundary labels overlapped their descriptions;
  - sample chip used generic `Статус`;
  - QA gates did not mention the Krisp reference matrix.

`V8 07`, `V8 08`, and `V8 09` had no mechanical findings in this pass, but
their screen-specific product gates were still re-checked.

## Figma Corrections Applied

| Frame | Correction |
|---|---|
| `V8 10` | Replaced browser hint with `Кабинет / встречи`; shortened the upcoming meeting row; changed table header to `Состояние`; changed upload row title from `client-call.mp4` to `Звонок с клиентом`; changed processing action to `Подробнее`; spaced bottom filter chips. |
| `V8 11` | Replaced browser hint with `Кабинет / встреча`; separated playback time from the `2 дорожки` chip. |
| `V8 12` | Replaced browser hint with `Кабинет / доступ`; narrowed export format labels to avoid button overlap; added external/outside-control deletion truth. |
| `V8 13` | Changed light-theme file-title row to `Звонок с клиентом`; changed vague action to `Подробнее`. |
| `V8 14` | Changed sample chip to `Готово`; fixed ownership label/description widths; added `Krisp-матрица` to the IA QA gate. |

## Post-Fix Audit Result

Targeted Figma API audit after corrections returned:

- missing target frames: `0`;
- bad controls: `[]`;
- text overlaps: `[]`;
- forbidden visible text hits: `[]`.

Screen-specific gates after correction:

| Frame | Required gates | Result |
|---|---|---|
| `V8 07 - Транскрипт и спикеры в приложении` | transcript, playback, outcomes, speaker entry | PASS |
| `V8 08 - Дорожки назначения спикеров` | separate speaker lanes, save action, percentages | PASS |
| `V8 09 - Настройки записи и темы` | recording policy, theme/language, storage/privacy/diagnostics | PASS |
| `V8 10 - Веб-кабинет: встречи и фильтры` | inline search, inline filters, human upload title, `Подробнее` action | PASS |
| `V8 11 - Веб-детали встречи и транскрипт` | transcript, playback, outcomes, governance actions | PASS |
| `V8 12 - Поделиться, экспорт, удаление` | share/export/delete coverage, truthful outside-control boundary | PASS |
| `V8 13 - Светлая тема: проверка экрана` | meetings, human upload title, `Подробнее` action | PASS |
| `V8 14 - Правила интерфейса и QA` | Krisp matrix gate, no-technical-copy rule | PASS |

## Remaining Limit

This pass proves the current Figma nodes satisfy the defined V8 07-14 mechanical
and product-gate checks. It does not replace stakeholder visual approval. The
design remains an active review candidate until the user explicitly accepts the
screen set for implementation handoff.
