# UX Checklist: удобные итоги встречи

## Information architecture

- [X] Первый вопрос пользователя («о чём?») обслуживается «Кратко».
- [X] «Действия» и «Решения» находятся до вторичных сигналов.
- [X] Все восемь truth-state категорий остаются проверяемыми.
- [X] Пустые/неопределимые секции не конкурируют с готовыми результатами и
      собраны в одном закрытом disclosure.

## Interaction and trust

- [X] Owner/due показываются только из сохранённых полей, без placeholder chips.
- [X] Source timecode ведёт к существующему player/transcript seek.
- [X] Processing, blocked, unsafe и unavailable имеют bounded next meaning.
- [X] Candidate acceptance и текущий accepted outcome не смешиваются.
- [X] Нет второй export CTA внутри самого summary; используется существующее меню.
- [X] Нет fake checkbox, task manager, retry или assignment promise.

## Accessibility and responsive behavior

- [X] Semantic headings, labelled buttons, keyboard tabs and focus-visible
  states определены в контракте.
- [X] State meaning не зависит от цвета.
- [X] Длинный outcome text и metadata переносятся.
- [X] Mobile 390 CSS px не имеет horizontal overflow и fixed player не закрывает
  primary content.
- [X] Web and embedded routes сохраняют parity.

## Brand and evidence

- [X] Используются существующие GRAF tokens/components/assets.
- [X] Не копируются competitor layout/assets/marketing copy.
- [X] Runtime evidence использует synthetic content only.
