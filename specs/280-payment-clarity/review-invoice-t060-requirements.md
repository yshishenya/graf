# Независимая проверка требований T060 — безопасная помощь и время браузерной проверки

Дата: 2026-10-04. Reviewer: `/root/sdd_supplement`. Полоса: `high-risk-product`, продолжение F280/FR049/052/SC016/017; reviewer-owned проверка качества требований до кода.

**REQUIREMENTS PASS: 16 checked, 0 unchecked.** Незакрытых критических/высоких/исправимых средних замечаний к проверенным требованиям: 0/0/0. Это заключение о качестве требований, а не о выполнении T060 или готовности производства. Независимые проверки кода, браузеров, текущие CI, слияние, release-full, dry-run/execute и live остаются последующими воротами.

## Границы и прочитанные источники

Workspace `/Users/yshishenya/.codex/worktrees/billing-simple/crisp`; `.specify/feature.json` определяет F280/`specs/280-payment-clarity`/`codex/280-invoice-consistency`. HEAD до реализации `31a9e7c8b3eb2695d416e94171b6729121e42744`. Прочитаны actual spec, plan, tasks, contract, quickstart, scoped analyze, checklist; root AGENTS/guidance index, spec-kit-flow/product-gates и применимые положения конституции. Использован проектный `speckit-checklist`: новые пункты оставлены сначала unchecked, затем отдельно оценены reviewer. Enabled state-changing hooks для checklist отсутствуют; Git не изменялся.

Reviewer владеет только `checklists/invoice-consistency.md` и этим новым отчетом. Canonical документы, код, задачи, PR/issues, Git, commits, release и deploy read-only. Чужие изменения сохранены. Suites не запускались.

## Новые пункты и устраненное замечание

CHK015/016 первоначально добавлены `[ ]`: 14 checked, 2 unchecked. CHK015 нельзя было подтвердить по первой редакции, которая без исключения требовала нормализацию display-name для всех пяти представлений. Read-only source показывает прежний account_merge фильтр `parsed != normalized`, где normalized означает stripped конфигурацию (`cabinet/web_routes/account_merge.py:164–174`), и сохраненный negative test `test_account_merge_contract.py:438–446`, отклоняющий `Display <support@example.test>`. Общая проверка безопасности не дает оснований расширять допустимость контакта при объединении аккаунтов.

Root внес одинаковое исключение в spec:420, plan:291, contract:163, quickstart:323, tasks:320, analyze:67 и обновил критерий issue #7534. Reviewer прочитал новые bytes и issue через read-only `gh issue view`. Строгий account_merge запрет имени сохранен; там общий parser/кодирование дополняют прежнюю политику. Остальные представления сохраняют допустимую нормализацию общего billing parser. Task:318 и analyze:65 требуют общего безопасного представления и прежних auth решений; финальные tasks:320 и analyze:67 также явно повторяют строгий запрет account_merge display names. Reviewer перечитал все шесть окончательных документов после этой синхронизации. Дополнительное редактирование canonical reviewer не выполнял.

CHK016 определен численно: внешний Python subprocess120→300 секунд. Прежний `test_billing_accessibility.py:403–407` завершает весь Node runner; `billing-accessibility.test.cjs:57` содержит отдельный action default5000ms. Требования запрещают менять assertions, каждый action limit, HTTP15 секунд, окно60 секунд, попытки и финансовые таймеры; runner/матрица/зависимости остаются прежними. Значение300 — конечный бюджет общей проверки, не доказанный математически минимальный предел и не основание скрыть содержательный отказ.

Прочитаны исторические `/tmp/f280-invoice-combined-webkit-timeout-history.log`: 1 failed/15 passed120.67s с `subprocess.TimeoutExpired` на120s; `/tmp/f280-invoice-combined-webkit.log`:16 passed97.35s. Они обосновывают отдельный внешний бюджет, не считаются текущими T060 испытаниями. Новые Chromium/WebKit на окончательных bytes предусмотрены quickstart/tasks.

## Основания для всех пунктов

| Пункт | Итог | Фактические основания качества требований |
|---|---|---|
| CHK001 | PASS | Spec FR046: состав основного блока, вторичная история и максимум одно доминирующее действие; tasks T052/T054 связывают реализацию. |
| CHK002 | PASS | FR046/052, plan invoice и T054: согласование с подпиской, ширина720, прежние owner boundaries; чужие денежные условия не копируются. |
| CHK003 | PASS | FR047 и acceptance1/2 разделяют создание, оплаченные границы и текущую активность. |
| CHK004 | PASS | FR047/048, contract invoice: viewer timezone, short/exact period, несколько storage intervals, nullable unknown/invalid и только month/year labels. |
| CHK005 | PASS | FR048, T052/T053: только действительная ненулевая скидка/безопасный номер, старые payer privacy guards. |
| CHK006 | PASS | FR049 и T060: раздельные темы вопроса/возврата, письмо не отправляет действие, общий безопасный fallback, без секретных данных. |
| CHK007 | PASS | FR050 и T059/contract: единственная conditional receipt-only форма по can_refresh_receipt с точным endpoint/CSRF; unavailable/default/false и конкурирующие деньги запрещены. |
| CHK008 | PASS | FR048/051 сохраняют service_gap/pending/recovery вне раскрытия и финансовую истину FR031–038. |
| CHK009 | PASS | Invoice scope/clarify, FR019/020 и contract: сохраняется checkout consent и session policy, invoice срез ее не переопределяет. |
| CHK010 | PASS | FR012/052, acceptance6, quickstart: нативные раскрытия, клавиатура/фокус, контраст, темы,320px/200%, JS-off. |
| CHK011 | PASS | FR014/052, research/конституцияVII: независимый код, права на активы, private screenshots внеgit, ограничения Krisp и внешних рекомендаций. |
| CHK012 | PASS | SC016/017, acceptance1–7 и coverage T052–T056; T060 добавляет проверяемые contact/timeout negative/positive состояния. |
| CHK013 | PASS | SC017, T055/T056, quickstart: exact frozen release-full/live отдельно; F278, человеческие SC005/006 и installed Dev не закрываются синтетикой. |
| CHK014 | PASS | Scope/T059/T060/FR011/019/020: узкие старые receipt/copy compatibility и безопасное представление existing help; новые денежные/auth решения, страницы, API/DB/flags исключены. Формулировка checklist явно дополнена T060. |
| CHK015 | PASS после clarify | Spec414/420, plan287/291, contract161/163, quickstart321/323, T060318/320, analyze65/67 и issue7534: все пять sibling представлений плюс blockers, plain display/copy отдельно от encoded href; missing/malformed/controls/encoded CRLF и checkoutfalse/observation-only покрыты; строгий account_merge фильтр сохранен. |
| CHK016 | PASS | Spec416/418, plan289, contract161, quickstart321, T060318: бюджет300 только enclosing subprocess; full77×5×2×2, все содержательные/action/product limits неизменны; исторический timeout сохраняется, нужны новые fingerprints/exactSHA/base. |

Issue #7534 существует, OPEN, имеет canon title `[280][P1][billing] T060: Сохранить безопасную помощь и надежную браузерную проверку`, связь F280/T060/PR7532, девять требуемых секций и labels feature:280/priority:P1/area:billing/gate:pr-blocker/type:bug. Это read-only проверка конкретной задачи, не утверждение о полном репозиторном canon validator. В tasks T060 остается `[ ]`.

## Повторное чтение и предел заключения

Reviewer повторно прочитал итоговый checklist после отметок: CHK001–016 уникальны, **16 checked, 0 unchecked**. Неподтвержденных пунктов качества требований нет. Прежние14/0 T059 notes сохранены как история; новый PASS относится к указанным ниже bytes.

Requirements gate разрешает перейти к запланированному причинному RED и реализации при остальных обязательных воротах root. Новые support helper, реальные GET/DB, браузерная матрица300s, независимые source/visual, CI текущего SHA/base и release еще не проверены этим reviewer. Нет утверждения merge/deploy/live/финансового/человеческого PASS. Чужой frozen50e и GRAF Dev не изменялись.

## Отпечатки окончательно прочитанных файлов

| Файл | SHA-256 |
|---|---|
| `spec.md` | `61c563b547445b3ecf87320b4c76dc9da4c7f0696f1a4aa4d45d93f44ebbd0b4` |
| `plan.md` | `552d07859133e6cbc13d406d3b8a7b0fa7a5048fc3961b8cd350b74728aac981` |
| `contracts/payment-journey.md` | `d4a978458662267e4c7d48bbbae5b344c959a46d92fed81cbe8331ef57ed4d49` |
| `quickstart.md` | `9cc7e590bf3a79eb728e9935fe9116b852f3006a2cca0668011667d0f409c2df` |
| `tasks.md` | `4569be64b41be05bf0079f468e9becff595309c9877a03db4af0543ea65b24b5` |
| `analyze-subscription-clarity.md` | `2621945c7ecc95d78cdd53ec47f70e605a47e1f6b982903b1e37c8c82160bcd6` |
| `checklists/invoice-consistency.md` | `622d1670076143310393d65a396fe22bf56fad4dcf08284adea22a49b563bcdf` |

