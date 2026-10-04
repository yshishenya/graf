# Независимый обзор требований — согласованность платежа F280

Дата: 2026-10-04. Полоса проверки: independent requirements review, high-risk-product / active Spec Kit slice. Основа: интегрированные рабочие документы `specs/280-payment-clarity`; исходный HEAD `d8fa0edb62d4b034f70e15b2c1321bdcb73ef3ac`. Документы еще не закоммичены; этот SHA не объявляется SHA проверенной реализации.

Reviewer владеет только `checklists/invoice-consistency.md` и этим отчетом. Код, canonical spec/plan/tasks/research/contract/data-model/quickstart, GitHub, коммиты и выпуск не изменены reviewer. Проверены существующие артефакты, а не только внешнее supplement. Supplemental документ использован для области назначения; действующие требования имеют приоритет.

## Решение после повторного чтения

**PASS: 14 checked / 0 unchecked.** В первом проходе единственный MEDIUM — research620 против plan/tasks720 — оставил CHK002 открытым. Canonical писатель исправил research.md:275 до720; reviewer перечитал эту строку, plan259/269 и T054. Также перечитаны уточнение FR049 про недопустимый support адрес и tasks с связями #7514–7518. Текущих CRITICAL0, HIGH0, исправимыхMEDIUM0. Checklist gate по требованиям выполнен; приемка кода/CI/release остаётся отдельной.

## Evidence по четырнадцати пунктам

| Пункт | Результат | Доказательство полноты требований |
| --- | --- | --- |
| CHK001 | PASS | `spec.md:361`, acceptance1/3, `contracts/payment-journey.md:143`: назначение, сумма, результат, срок, хранение/чек на виду; история перед основным содержимым, помощь в нативном раскрытии, не более одного доминирующего действия. |
| CHK002 | PASS после correction | Геометрия720 и владение согласованы `research.md:275`, `plan.md:259/265/269`, T054; checkout620 прямо остается без изменения. Независимость/истинность GRAF в FR052/research. Reviewer повторно прочитал исправленные canonical файлы. |
| CHK003 | PASS | FR047/048 и acceptance1: invoice.created_at — «Дата создания платежа», не подтверждение денег; исторический/будущий платеж не объявляет активность текущего тарифа. `data-model.md:38–40`, contract143. |
| CHK004 | PASS | FR047/048, acceptance2; data-model38–41: одна viewer-local зона, nullable недостоверные границы, известные month/year, сохранение storage_segments. Quickstart305: malformed/unknown cycle, UTC-cross-midnight, viewer-local; T052/053. |
| CHK005 | PASS | FR048: безопасный номер/copy и ненулевая действительная скидка, маскированные доступные реквизиты, прежний payer/privacy; acceptance4/7, quickstart303/305, T052–055. |
| CHK006 | PASS | FR049, acceptance5, plan263, contract145, data-model42/45: два статических намерения, проверенные email/safe_number, прежняя refund-обертка, без секретов/чужих URL и автоматической отправки/возврата, запасной help. |
| CHK007 | PASS | FR050, acceptance4, contract145, data-model43: зарегистрированное состояние плюс допустимая ссылка плюс текущие права, AVAILABLE без URL не создает действие; unknown/registering/payer-only остаются правдивыми. T052/053/054/055. |
| CHK008 | PASS | FR048/051, acceptance3/7, contract143/147: service_gap и финансовая истина вне details; все прежние FR031–038, атрибуты, сообщения, live regions, восстановление и лимиты неизменны. Quickstart303 требует существующую status matrix при class правке. |
| CHK009 | PASS | `spec.md:353–356`, FR019/020, contract149, research278: прямое решение владельца «прежний предвыбор везде» имеет приоритет над ранним макетом off. Сохранение явного выбора в непрерывном оформлении по FR020 не отменяется. Срез не меняет consent/checkout/JS/денежные пути. |
| CHK010 | PASS | FR012/052, acceptance6, contract143/147: клавиатура/видимый фокус, нативное раскрытие, темы/контраст,320px/200%; quickstart303 включает оба движка/320/390/768/1280/темы/клавиатуру/JS-off. Copy остается существующим дополнением; safe_number текст доступен без JS. |
| CHK011 | PASS | FR014/052, plan257/259, research274–280 и прежний provenance268: собственный код/ресурсы, без сторонних активов, правдивые собственные условия, приватные источники вне git, NN/g2006 не объявляется новым экспериментом; источники не доказывают конверсию GRAF. |
| CHK012 | PASS | SC016/017 и семь acceptance371–377 измеряют нулевое создание финансовых объектов/provider calls на чтении, один уровень реквизитов, отсутствие overflow и независимые gates. Все FR046–052 и SC016/017 имеют T052–056; quickstart включает state/DB/browser/negative matrix. |
| CHK013 | PASS | SC017, scope386, quickstart307/309, T055/056: source/current SHA/merged/frozen Full/dry-run/execute/live отдельны; установленный GRAF Dev, F278 и human SC005/006 не закрываются synthetic. Выпуск зависит от обеих готовых реализаций, чужие frozen records защищены. |
| CHK014 | PASS | Clarification355/356, scope386, plan255/261/265, contract147/149, data-model34/45: нет новых permission/data/API/DB/browser state, новой истории, изменения subscription/checkout/JS/money/scheduler; только invoice projection/layout и минимальный status class при необходимости. |

## Разделение проверок

Проверка подтверждает достаточность требований. Наличие тестовых сценариев и названий команд не означает их выполнение. Реальные financial/provider/mail/refund действия reviewer не выполнял. Не доказаны готовность реализации, конкретный кандидат PR, CI, выпуск, установленный Dev, банк/чек/возврат, люди или конверсия.

Конституция §VI/VII и product gates прочитаны: reference-fidelity допускается при независимом коде, сохранении доступности/приватности/денежной истины; требования им не противоречат. `spec-kit-flow.md` требует независимого checklist и analyze до кода, canon sync принадлежит координатору. У `speckit-analyze` before/after hooks отключены; reviewer не выполняет mutations. Рабочий prerequisite вызван штатно с `--json --require-tasks --include-tasks` и подтвердил тот же FEATURE_DIR; `--require-spec` данным скриптом не поддерживается.

## Coverage среза

| Требование | Задачи |
| --- | --- |
| FR046 | T052/T054/T055 |
| FR047 | T052/T053/T055 |
| FR048 | T052/T053/T054/T055 |
| FR049 | T052/T053/T054/T055 |
| FR050 | T052/T053/T054/T055 |
| FR051 | T052/T054/T055 |
| FR052 | T052/T054/T055 |
| SC016 | T052–055 |
| SC017 | T055/T056 |

Девять требований/критериев этого продолжения покрыты задачами9/9=100%; задачи T052–056 mapped5/5. Непокрытых и лишних задач в срезе0; SC005/006 — отдельные human/outcome metrics, не buildable scope. Последовательность RED→projection→layout→validation→общий release определена. Используется существующий `test_billing_clarity.py`, новая parallel suite не нужна. Changelog `F280.yaml` принадлежит единственному писателю. Это scope-limited review; исторические T001–051 не перепринимаются.

## Независимый scoped analyze интегрированных артефактов

Операция analyze выполнена без изменения canonical или кода. Использованы spec FR046–052/SC016–017 плюс применимые FR011/012/014/019/020/031–045, plan253–269, research270–280, data-model32–45, contract141–149, quickstart278–309, tasks282–297 и Constitution §VI/VII/quality gates. Покрытие требований/задач приведено выше.

| Проверка | Результат |
| --- | --- |
| Constitution alignment | Нарушений0; high-risk lane, независимый checklist/analyze/review, честные financial/live ограничения, доступность и own implementation сохранены. |
| Cross-artifact consistency | Текущих конфликтов0; stale620 исправлено. FR019/020 не меняются, invoice projection не создает новых monetary/state/permission paths. |
| Coverage | FR046–052/SC016–0179/9=100%; T052–0565/5mapped, acceptance1–7 имеют серверную/браузерную/negative matrix. |
| Ambiguity / underspecification | Применимых blocking ambiguities0, исправимыхMEDIUM0; nullable периоды, неизвестный цикл, safe email/номер, чек без URL и прежний payer предусмотрены. |
| Duplication / ordering | Блокирующих дубликатов0; RED→projection→layout→validation→оба merged PR/frozen release. Исторические и чужие closeout не заменяют новые gates. |
| Unmapped tasks | В данном срезе0. SC005/006 — human/outcome; не входят в buildable denominator. |

Связи issues подтверждены только наличием в прочитанном tasks: T052#7514, T053#7515, T054#7516, T055#7517, T056#7518. Это не независимое чтение GitHub issue bodies/labels либо canon validation. Они остаются ответственностью координатора.

Практический предел: diff --check обнаружил только лишнюю пустую строку в конце plan.md:270; это механическое оформление, не требовательное MEDIUM и не причина блокировать требования. Исправлять вправе canonical писатель; reviewer его файл не менял.

Итоговый checklist перечитан после записи:14 checked/0unchecked. REQUIREMENTS PASS и scoped ANALYZE0CRITICAL/0HIGH/0исправимыхMEDIUM разрешают следующий RED/implementation шаг при отдельно выполненном canon sync. Реализация, runtime/installed/live/финансовая/человеческая приемка этим решением не закрыты.
