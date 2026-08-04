# Candidate review evidence

- Дата: 2026-08-04
- Контент: synthetic
- Screenshots: `04-after-candidate-desktop.png`,
  `06-after-candidate-mobile.png`, `12-reference-disclosure-desktop.png`,
  `13-reference-disclosure-mobile.png`

## Runtime assertions

| Проверка | Desktop 1280×720 | Mobile 390×844 |
|---|---:|---:|
| Horizontal overflow | 0 px | 0 px |
| Primary IA | Кратко → Действия → Решения | Кратко → Действия → Решения |
| Owner/due | present | present |
| Candidate source refs | 7 canonical refs; refs 3–4 раскрываются через «Ещё 2» | 7 canonical refs; refs 3–4 раскрываются через «Ещё 2» |
| Secondary sections | collapsed | collapsed |
| Internal prompt/generator/candidate keys in visible copy | 0 | 0 |
| Explicit decisions | Оставить текущие / Использовать | Оставить текущие / Использовать |

Статус сокращён до: «Вариант „Авто“ готов. Текущие итоги сохранены.»
Счётчик пунктов исключён как лишний и грамматически хрупкий.

## Interaction assertions

- «Оставить текущие» получает HTTP success, скрывает candidate status и preview,
  оставляя сохранённые итоги видимыми.
- «Использовать» получает HTTP success, перезагружает detail view и больше не
  показывает candidate state.
- Source action переключает вкладку на «Расшифровка», фокусирует точную
  synthetic speaker turn и объявляет «Открыт источник 00:12 в расшифровке.»
- Native disclosure «Ещё 2» сохраняет первые две ссылки в основном потоке,
  раскрывает ссылки `00:42` и `00:57` и не создаёт horizontal overflow.
- Клик по четвёртой ссылке выбирает segment `…0142`, открывает вкладку
  «Расшифровка», фокусирует соответствующий turn и объявляет
  «Открыт источник 00:57 в расшифровке.»
