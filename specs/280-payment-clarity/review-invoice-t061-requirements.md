# F280 T061 — независимая проверка существующих требований до реализации

2026-10-04. Reviewer `/root/subscription_final_findings`; ownership только этот отчет в /tmp. Другие участники работают в репозитории; их файлы и изменения не тронуты. Код, tests, specs/plan/tasks, checklist markers, Git/GitHub, provider/deploy read-only. Тесты reviewer не запускал. HEAD лично проверен: `11d2b2d35e9c7f0f723ec92f79ad0d572b0c9778`.

**REQUIREMENTS PASS: existing invoice checklist покрывает узкую test-only T061 поправку; 16 checked, 0 unchecked после повторного чтения полного checklist. Новых требований/пунктов и изменения маркеров не требуется. CRITICAL0/HIGH0/исправимых MEDIUM0 пробелов требований.** Это достаточность существующих требований до реализации, не утверждение об исправленном тесте или выпуске.

## Что проверено независимо

Прочитан reviewer-owned `specs/280-payment-clarity/checklists/invoice-consistency.md` целиком, затем перечитан и подсчитан повторно. FR049, FR052, existing invoice context и актуальные исходники сопоставлены с конкретным failing assertion. FR049 требует отдельные вопросы/возврат, безопасный контакт, отсутствие автоматической отправки/возврата, отсутствие статуса возврата в GRAF и независимость автопродления. FR052 требует доступность нативного раскрытия, ясную подпись, клавиатуру и фокус. Эти продуктовые требования уже действуют; test-only T061 их не меняет.

CHK006 покрывает смысл и безопасность помощи/возврата; CHK010 — доступность раскрытия. CHK012 требует объективной проверки приемочных состояний, CHK013 — раздельные уровни доказательств; CHK014 ограничивает продуктовые/денежные изменения. CHK007 сохраняет отдельную legitimate receipt-only форму по can_refresh_receipt: T061 не превращает локальное `no form` ожидание fixture без этого разрешения в общий запрет формы проверки чека. Остальные пункты checklist не затрагиваются, прежние 16 маркеров оставлены без изменений.

## Причина и достаточность минимальной поправки

`apps/server/tests/contract/test_billing_clarity.py:284–305` создает `Page` с закрытым нативным details, проверяет скрытость результата возврата и затем моделирует раскрытие через замену устаревшего `<details class="billing-coupon">`. В текущем `billing_invoice_content.html` оба раскрытия используют `settings-disclosure`; замена не находит ни одного блока, поэтому текст после открытия не появляется в `expanded.visible`.

Прочитан Page.handle_data: при details без open он намеренно скрывает текст, кроме summary. Следовательно, недоступность текста здесь является следствием неверной имитации открытия в тесте, а не исчезнувшего продуктового предупреждения. Текущий шаблон действительно содержит все четыре проверяемые фразы, ссылку `/billing/subscription` и нативный summary «Помощь и возврат».

Достаточна единственная test-only замена selector literal, ограниченная help/refund:

```python
html.replace(
    '<details class="settings-disclosure"><summary>Помощь и возврат</summary>',
    '<details class="settings-disclosure" open><summary>Помощь и возврат</summary>',
)
```

Это меняет только имитацию открытия нужного блока, не раскрывает также «Сведения о платеже». Не нужны новый parser/helper, новая fixture, dependency, product edits или изменение класса обратно. Сохраняются прежние assertions: сумма и подпись видны до открытия, результат скрыт до открытия, четыре ограничения видны после, переход управления продлением существует, form в этой fixture отсутствует. Сохранение существующих assertions является условием разрешенного объема T061, а не будущим PASS.

## Обязательное доказательство после реализации

1. Причинный RED точного теста на исходном selector; без продуктовых правок.
2. GREEN того же теста после изменения selector с прежними assertions.
3. Полный touched файл `tests/contract/test_billing_clarity.py`, review diff и lint по выбранной полосе проверки.
4. Normal PR с current exact-SHA/base обязательными gates. После нового SHA — новый frozen candidate и успешный authoritative release-full до deploy; старое доказательство не переносится.

Первоначальный release-full run37178472845 для frozen11d2 имеет shard1 failure по сообщению оператора. Reviewer не читал artifact этого run в данной узкой проверке, поэтому не представляет это сообщение как собственный live API результат. Ни этот run, ни старый candidate не получают PASS из данного отчета. Будущие GREEN/full/CI, фактическое браузерное раскрытие, production и финансовая приемка здесь не подтверждены.

## Отпечатки до реализации

| Файл | SHA-256 |
|---|---|
| invoice-consistency checklist | `622d1670076143310393d65a396fe22bf56fad4dcf08284adea22a49b563bcdf` |
| spec.md | `61c563b547445b3ecf87320b4c76dc9da4c7f0696f1a4aa4d45d93f44ebbd0b4` |
| test_billing_clarity.py | `570b7b24db080dffa8ef79d28f8bdc0a6b68b6e662cd64fe9453b710a5054341` |
| billing_invoice_content.html | `d59cc28d1608f1dd3f3783f2d8a621503b80f4fcdb836ab888f4bad7fbf3f9a4` |

Итог: требования достаточны для этой узкой test-only поправки. Допуск не разрешает ослабить проверки, поменять денежные условия/БД/флаги или объявить прежний неуспешный frozen full успешным.

## Узкий refresh после append-only T061

Прочитан current tasks Phase27/T061 и quickstart T061: объем, сохранение всех прежних assertions и parser, targeted causal RED→GREEN/full touched file, independent requirements/source review, normal PR и новый candidate/full явно описаны. Новых продуктовых решений или противоречий FR049/052 нет. Отдельный causal peer report `временное локальное доказательство оператора` и JSON прочитаны: old selector0, current details2, все четыре raw пояснения, subscription link/no-form/closed-state сохранены. Это независимый диагноз в памяти, не будущий GREEN измененного файла; его предложение открыть оба текущих details сужено здесь до semantic Help/refund target согласно заданию root.

Checklist hash после current T061 остался `622d1670076143310393d65a396fe22bf56fad4dcf08284adea22a49b563bcdf`; totals16/0 сохранены. Current tasks SHA256 `e7ba1f96b7e3032718d9a61d1bd341992100463915d0e60aca06c9c2de10f28a`; quickstart `c8d347efcdc8abc630b8b01a1d682434696b604f64615309c849cf0e17a38c5a`. Scope не требует менять checklist marks или spec/plan. Требования достаточны до реализации; финансовый/release гейт по-прежнему отдельный.

Прочитан и actual scoped analyze `analyze-subscription-clarity.md:69–71`: связь FR049/052→T061→полный touchedfile→source review→новые exactSHA/base/full/release явно сохраняется, acceptance waiver нет. Его CRITICAL0/HIGH0/fixableMEDIUM0 согласуется с самостоятельной оценкой выше; pass analysis не заменяет будущий test GREEN.
