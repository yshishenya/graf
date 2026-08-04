# End-to-end journey evidence

- Дата: 2026-08-04
- Контент: synthetic
- Mobile matrix: `11-mobile-state-matrix.jpg`

## Entry/state matrix

| Journey | Проверенный результат |
|---|---|
| Owner accepted | Кратко → Действия → Решения; owner/due видимы; первые 2 source refs остаются компактными, refs 3–4 раскрываются через «Ещё 2»; overflow 0. |
| Ready candidate | Current accepted truth остаётся на месте; compact localized preview; accept/reject работают. |
| Processing | «Транскрипт готовится» встречается один раз; нет fake transcript/source action; overflow 0. |
| No player/transcript | Accepted summary остаётся доступным; source controls и labels отсутствуют; player отсутствует; overflow 0. |
| Summary-only | Локализованный HTML, не JSON; Кратко → Действия → Решения; owner/due видимы; transcript content/source actions отсутствуют; overflow 0. |

## Keyboard/focus evidence

- Source action: hash `#recording`, selected tab «Расшифровка», exact
  `data-source-segments` turn focused, live region обновлён; проверены canonical
  refs `12.5s` и `57.5s`, playback затем продолжает время.
- Timeline `Enter`: synthetic 120-second track seeks to midpoint (`≈60s`) and
  keeps focus on the timeline control.
- Heading snapshot сохраняет единственный page `h1`, скрытый structural `h2`,
  затем visible content headings без пропуска semantic outline.

## Visual review

`10-baseline-vs-after.jpg` объединяет baseline и final prototype при одинаковом
desktop viewport. Final candidate заменяет плоский технический список на
локализованные outcome sections, не вводя новые dashboard/card IA, навигацию или
design tokens.
