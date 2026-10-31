# T106 — настоящий SDK и сохранение очереди, 01.11.2026

Lane active Spec Kit slice/privacy browser. Исходная база
94c40e0b78da2e222c0318ded5d89f0c8174f012; product flags/consent revision
не менялись. Полная T106/#7696 остаётся открытой.

## До кода

Independent public-sdk-network checklist5/0, C/H/M0 scoped analyze,
coverage4/4 FR-001/003/006/049, owner7696 OPEN, canon ensure/validate PASS.
Первый SDK запуск с прежним fixture render_only честно FAIL: SDK намеренно
не загружается. Independent уточнение5/0 приняло только учебный provider_smoke.
Повторный analyze C/H/M0 и issue sync6549995523 фиксируют это до product JS.

Настоящий integrated RED после этого: отказ сохранён, disable=true и вызов
destruct присутствует, но instance остаётся. SDK Bi подписывается на push
исходного ym.a, а GRAF filter заменял массив и терял подписку. В отдельной
диагностике прямой instance.destruct удалил instance. Диагностических вызовов
и обёрток ym в принятом CLI нет. Independent root requirements review5/0,
повтор analyze C/H/M0 и sync6550026404 предшествовали product JS.

Node RED с custom push упал на потере identity исходного массива. Минимальный
reverse splice сохраняет массив/SDK push, удаляет только команды своего ID;
общий helper обслуживает public и product ID. Node GREEN:18сценариев,0skips;
проверены array/push identity, обработка destruct и сохранение чужой команды.

## Настоящий интеграционный GREEN

SDK SHA25672dadb1a319174bf611e44d0a70ed9569fb3c72fdd685223ac6091fc3ef0db9e,
источник/время получения в public-sdk-research-20261101.md. Input только явный
локальный файл+SHA, missing/hash mismatch проверены —exit1 до браузера.
Использован уже установленный Playwright; новых зависимостей нет.
Реальные GRAF controller/CookieConsent, analytics-only, counter99999999,
provider_smoke только synthetic config. Новый непостоянный context на сценарий,
serviceWorkers blocked, HTTP fulfilled/aborted и WebSocket closed до SDK;
route.continue/fetch отсутствуют. SDK не изменялся и не попадает в Git.

| Страница | Отказ | Watch до | Попытки после | Наблюдение |
| --- | --- | ---: | ---: | ---: |
| / | same-tab | 3 | 0 | 20s |
| / | cross-tab | 6 | 0 | 20s |
| /download | same-tab | 3 | 0 | 20s |
| /download | cross-tab | 6 | 0 | 20s |

Все участвующие вкладки имели настоящий instance до отказа; затем он исчез.
Выбор через реальную CookieConsent, shared storage/events настоящие. После
границы отказа учитываются все optional attempts, в том числе abort/relay/WS,
затем click/scroll/focus/resize/visibility и20s. Во время normal пробы нет
подмены SDK/ym или прямого instance.destruct. Forwarding отсутствует.

Причинный negative control: собственная временная копия CLI подавила только
ym destruct после positive control. Exit1 ровно instance-still-present,
как ожидается; copy удалена finally. Это проверка обнаружения оставшегося
instance, не доказательство autonomous send при подавленном destruct.

Прежний scoped public/unit/contracts/consent/modal/PostHog/provider gate:
67passed,0skips,11.21s; реальный modal включён готовым Playwright.
Изолированная PostgreSQL удалена штатным runner. Process/governance/fragment/
JS syntax/diff PASS. Первый process check во время временной negative copy
отклонил её как не owned; после её штатного удаления повтор PASS.

## Воспроизведение и границы

Команда CLI в quickstart. Negative control исполнялся отдельным stdlib driver:
создал временную копию около исходного harness, вставил wrapper в явно
названную точку после positive control, проверил exit1/точную причину,
удалил копию в finally. SDK и подробные учебные журналы ignored; в Git
только тестовый код и этот отчёт без query/cookies/body/SDK идентификаторов.

Finite20s, analytics-only и локальные ответы НЕ принимают replay, настоящий
backend/settings/readback, global server permission, индивидуальный server
revoke, runtime, весь SDK/T106, измерение или T0. Внешнее включение HOLD.
Independent implementation review/converge и exact PR checks следуют отдельно.


## Исправление замечания независимого implementation review

Первое ревью нашло1P2 в harness: любое исключение ожидания превращалось
в instance-still-present. Теперь маркер возможен только для TimeoutError
и отдельного true чтения настоящего instance; неизвестная/иная ошибка
пробрасывается. Повторный negative control PASS на настоящем оставшемся
instance; дополнительная временная копия закрыла страницу после отказа —
exit1 с closed-page ошибкой, без ложного instance marker. Обе копии удалены.
Четыре normal сценария повторены на исправленном harness (сводка выше).
Продуктовый JS и прежние67regression результатов этой test-only правкой
не меняются. Окончательный independent re-review следует отдельно.

## Контрольные суммы принятого локального результата

- `analytics.js`: `2d05b53cd6087cfb80258687bc798e99d910bfde6249cadc4045ac444c08c0c1`.
- `public-analytics-sdk-network.test.cjs`: `8e42c8d02b09e1e20485f6e119c2f01c030f5ee6a50f2b498e09d9417691571b`.
- `integrated-result.txt`: `9f84a5bb3cd72a3051e0c44b39a6c30dca57c0946b1a3d05cf2074cc7f92f1ae`.
- `negative-result.txt`: `3cb98b337d367c9190335405c5bd5189fbff28c636d1bda15e17b3cc89761fa4`.
- `regression.txt`: `e91394a43d4236f0a05862d56faecb7faea988377e563bd39d593e9dea7d3c13`.


Финальный independent re-review/scoped converge PASS: checklist5/0,
P1/P2/HIGH0. Замечание P2 устранено, driver прочитан независимо. В рамках
согласованного SDK/cleanup среза новых пробелов нет; остаток широкой фичи
уже относится к открытым T106/T112/T113, дублирующие задачи не создаются.
Exact PR checks/merge и рабочая приёмка ещё отдельные шаги.
