# Независимая проверка требований административной навигации T069

Дата: 2026-10-16. База HEAD `c6dca30e522f3f1580a53cfdf2eeaf1b75683c84` плюс только текущие документальные уточнения перед исправлением. Владелец — `/root/independent_2_volume`; отдельное разрешение root разрешает менять только `checklists/ux-payment.md` и этот отчет. Исполнитель agent1 не менял reviewer-owned отметки.

**REQUIREMENTS PASS: 137 checked / 0 unchecked по11файлам.** Reviewer-owned129/0 + built-in requirements8/0; ux-payment24/0. Это допуск качества требований до product correction, не PASS реализации, тестов, CI/merge, выпуска или административных полномочий.

## Что проверено независимо

Прочитаны все11checklist файлов (актуальные checkbox-строки и относящиеся notes), FR008/012/SC017 и новые уточнения spec/plan/tasks/quickstart, общие требования неизменности платежей/приватности/согласий. Исторические REQUIREMENTS PASS не использованы вместо нового чтения применимого CHK024. Дополнительно прочитаны реальные admin/base.html, admin/admin.css, общий mobile NoJS блок cabinet.css, admin/view_models.py и кабинетный sections marker. Самостоятельное исходное заключение `.dev/closeout-five-agent-20261016/review-admin-navigation-gap.md` установило отсутствие явного admin покрытия до уточнения.

## Основания CHK024

| Проверяемое требование | Актуальное основание | Итог |
|---|---|---|
| Сохранение других потребителей общей CSS | Spec «Уточнение совместимости T069»: нет cabinet ready flag не разрешает скрыть admin меню; data-admin-shell остается без cabinet.js | PASS |
| Узкая область исправления | Plan «T069 — область общего CSS»: ограничить только добавленное sidebar-hide существующим положительным data-cabinet-shell, без новых правил/admin exceptions | PASS |
| Реальный потребитель и реальный набор ссылок | Plan+Quickstart: настоящий admin/base.html, cabinet.css → admin.css и штатный admin_navigation; view_models.py содержит ровно7items; запрещены искусственные data-cabinet-shell/data-cabinet-js/cabinet.js в admin fixture | PASS |
| Наблюдаемая доступность | Quickstart: sidebar, все7ссылок, клавиатурный переход в «Пользователи», сохранение shell после перехода; Spec требует видимую/клавиатурную навигацию | PASS |
| Матрица и причинность | Quickstart: causal RED320/360/980 с контрольным1280, Chromium/WebKit, обе темы и JS on/off; затем GREEN. Это16сочетаний на движок/32всего, без требования считать их отдельными pytest tests | PASS |
| Сохранность исходного T069 | Spec/Plan/Quickstart: прежние cancellation/reflow assertions и весь accessibility набор обоих движков, billing contracts, shell/admin unit не ослабляются | PASS |
| Прежний и новый evidence не смешаны | Tasks уточнение #7613: прежний PASS не покрывал admin; новый independent review/exactSHA gates. T070 и Full/CD/runtime/live отдельны | PASS |
| Нет новых полномочий/данных | Spec: цены/согласия/денежные маршруты/административные полномочия прежние; Plan: no new backend/DB/provider. FR019/020 default required unchecked offer/optional checked recurring сохранены | PASS |

Новый CHK024 сначала записан `[ ]`, затем отмечен после проверки всех оснований выше; CHK001–023 перечитаны с акцентом на роль/область/доступность/регрессию/изолированные приемочные границы. Остальные10файлов не изменены. Исходный общий grid rule не требуется переписывать для admin: admin.css задает display:block в узком диапазоне; ограничение только нового hide rule соответствует минимальной причине. Административный функционал/роль/БД не меняется.

## Перечитывание и подсчет после записи

| Checklist | checked | unchecked |
|---|---:|---:|
| invoice-consistency.md | 16 | 0 |
| optional-renewal.md | 10 | 0 |
| payment-return.md | 17 | 0 |
| promo-inline.md | 16 | 0 |
| promo-presentation.md | 6 | 0 |
| promo-refresh.md | 9 | 0 |
| provider-rejection.md | 10 | 0 |
| requirements.md | 8 | 0 |
| storage-simplicity.md | 7 | 0 |
| subscription-clarity.md | 14 | 0 |
| ux-payment.md | 24 | 0 |

Всего137/0; ux24/0. Другие checklist файлы сохранены побайтово относительно HEAD. Предыдущие136/0 относятся к прежнему покрытию и не доказывали admin navigation. Неподтвержденных пунктов требований в текущем узком уточнении не найдено.

## Снимок прочитанных документов

| Файл | SHA-256 |
|---|---|
| spec.md | `65b637937825e70ec33da965c4498a728a87eb7641541b9b8f708299bf1c3df0` |
| plan.md | `0f0de9cad46bbc5547cf2ed676e5a15f696e06fa9ab01aa09276049a3c94f59c` |
| tasks.md | `74d4bf2cabbe4edc8886372946b3984743c47b5056941f8a52f4d0143a8539a9` |
| quickstart.md | `c2cb3b46f64764e467ff1e2ca9d0b0f9bc96483ab52468c7043d3d9b4d0453d2` |
| checklists/ux-payment.md | `1f1bba124e5e1623e887f277d11f8ca2e2373eb44f61e981e8b7c77dc96340aa` |

## Оставшиеся ворота

Самостоятельно не выполнялись admin browser tests или product correction. Сообщенные исполнителем RED logs не используются как implementation PASS этого требования. Сначала причинный RED→GREEN и полные нужные повторные наборы, затем независимый source/browser обзор, convergence, новый exactSHA/base commonvalidator и actual merge. T069 вновь `[ ]` в текущем tasks.md, прежнее подтверждение сохраняется исторически; #7613 пока не закрывается; T070/#7614 дополнительно frozenFull/CD/tag/Release/runtime/live и явный release-ready root. T011/T012/SC005/006/F278 остаются отдельными открытыми критериями.


## Linux reflow, 2026-10-16

**REQUIREMENTS PASS — 137 checked/0 unchecked, ux24/0; runtime HOLD.** Новый проверенный committed source `c9f938851942c6f5c931ae57e5dfd9043d664769`. Root назначил независимый requirements refresh перед минимальным Linux исправлением. Изменены только CHK022/notes в ux-payment.md и этот отчет; новое checkbox/фича/платформенная архитектура не добавлены.

### Наблюдение и граница требований

Самостоятельно прочитаны failed governance-fast38846102759 и `.dev/pr7616-c9f938-governance-failed.log`: GitHub run на exact c9f938 завершен failure. Linux Python3.13.16; admin16real-base cases прошли, затем cancellation320/light/200%/JSfalse: left58/right322.203125/top410.5625/bottom489.9375. Исходный CJS assertion требует left≥−1, right≤width+1, top≥−1, bottom≤901, поэтому right322.203125 превышает допустимые321. Ошибка реальна для установленной приемки; ее нельзя объявить допустимой только из-за малой величины или локального macOS PASS.

У FR012/specSession2026-10-16 и T069 нет исключения Linux: кнопка/условия должны помещаться при320px/200%, в обеих темах и движках. В исходном CHK022 ОС явно не названа; это пробел явного описания validation coverage, а не отсутствующая новая пользовательская возможность. `docs/agent-guidance/release-and-validation.md` уже требует current exact-SHA governance-fast, а `.github/workflows/governance-fast.yml` использует ubuntu-latest и Chromium. Поэтому CHK022 узко уточнен о том же обязательном Linux evidence, без добавления новой ОС/нового workflow/новой матрицы сверх существующего процесса.

Повторно прочитаны CHK013/016/018/022–024, applicable subscription/invoice/storage accessibility и весь текущий checkbox-набор11файлов. Административный CHK024 сохраняется, ранее доказанный admin RED→GREEN не заменяет failing cancellation на Linux. Все прежние numeric limits/matrix/assertions сохраняются: не менять width+1, не уменьшать zoom/ширины/темы/JS-режимы, не подменять фактические границы scrollWidth и не прятать overflow. Пять агентных ролей и проверкаLinux не являются человеческой T012/SC005/006.

### Допуск требований и оставшаяся проверка

Текущие требования достаточно точны для причинного минимального исправления agent1; новых вопросов/данных/денежных решений нет. Requirements gate PASS не утверждает установленную причину переполнения: ее определяет исполнитель и независимо проверяет source/browser reviewer. Сначала сохранить Linux RED, минимальная product correction, GREEN с теми же assertions и применимостью среды, повтор затронутых полных Chromium/WebKit наборов и admin/billing/shell регрессий по существующему quickstart. Затем новый независимый final review, exact head/base GitHub commonvalidator и actual merge. До этого T069/#7613 не закрывать; T070/#7614 дополнительно требует explicit root release-ready и фактические frozenFull/CD/tag/Release/runtime/live proof.

### Перечитывание после записи

| Checklist | checked | unchecked |
|---|---:|---:|
| invoice-consistency.md | 16 | 0 |
| optional-renewal.md | 10 | 0 |
| payment-return.md | 17 | 0 |
| promo-inline.md | 16 | 0 |
| promo-presentation.md | 6 | 0 |
| promo-refresh.md | 9 | 0 |
| provider-rejection.md | 10 | 0 |
| requirements.md | 8 | 0 |
| storage-simplicity.md | 7 | 0 |
| subscription-clarity.md | 14 | 0 |
| ux-payment.md | 24 | 0 |

Итого137/0, reviewer-owned129/0+built-in8/0, ux24/0. Другие10checklists побайтово сохранены относительно c9f938. Предыдущие снимки/заключения выше исторические.

Текущие fingerprints требований:

| Файл | SHA-256 |
|---|---|
| spec.md | `65b637937825e70ec33da965c4498a728a87eb7641541b9b8f708299bf1c3df0` |
| plan.md | `0f0de9cad46bbc5547cf2ed676e5a15f696e06fa9ab01aa09276049a3c94f59c` |
| tasks.md | `98f4c2c7ef581a3b5f2fa7ca4408dff4cfc640791b7b27db645a0d0d98b91bea` |
| quickstart.md | `c2cb3b46f64764e467ff1e2ca9d0b0f9bc96483ab52468c7043d3d9b4d0453d2` |
| checklists/ux-payment.md | `97d06eb8cf4849e6a17c1b5eae0d04b00faa8b0c8d9bc5c8abf8171c4dfa8b70` |
