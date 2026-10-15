# Независимая проверка требований F280: отказ начала оплаты

Дата: 2026-10-01. Рецензент: `provider_rejection_requirements`. Рабочая копия: `release-f280/crisp`; активная фича подтверждена `.specify/feature.json` и `check-prerequisites.sh --json --paths-only`. Lane: проверка требований существующего среза `high-risk-product`, будущий выпуск `release-deploy`.

**Результат: PASS качества требований FR-021–023/SC-009 до окончательной генерации T023–T025.** Два найденных уточнения исправлены и перечитаны. Автор plan явно ограничил распознавание отказа schema2, отменённым состоянием, отсутствием provider_id, записанной class и целочисленным безопасным HTTP. Рецензент уточнил CHK008: запрет новой оплаты относится к неизвестному исходу; настоящая подтверждённая отмена сохраняет прежнюю возможность повторить. Неразрешённых CRITICAL/HIGH/MEDIUM замечаний требований нет. Этот PASS разрешает генерацию задач и последующие ворота, а не начало кода до analyze/issue sync.

Прочитаны текущие spec, plan, tasks, quickstart, research, data-model и contracts/payment-journey; каждый пункт всех шести активных чеклистов; конституция7.1.0; guidance README/spec-kit-flow/product-gates/release-and-validation и применимые разделы PRD/текущего статуса. В исходниках только прочитаны `_initial_checkout_failure_metadata`, `_record_initial_checkout_failure`, `_persist_initial_checkout_failure`, `_create_initial_checkout_payment`, статусный GET и `_request` адаптера. Это подтверждает границы существующего механизма, а не готовность будущего исправления. Исторический продуктовый статус не использован как доказательство нынешней настройки магазина.

## Основания нового чеклиста

| Пункт | Достаточное доказательство требований |
| --- | --- |
| CHK001 | FR-021/023 отличают отклонённое создание, подтверждённую отмену и unknown; plan задаёт ограниченный предикат: purchase_schema2, canceled, no provider_id, class provider_rejected, intHTTP400/401/403/404/405/415/429. Quickstart перечисляет отрицания schema1/bool/string/unknown class/bound/state. |
| CHK002 | FR-021/023 и plan называют сохранённую авторитетную операцию источником причины; quickstart требует отрицательную проверку подставленного query. Просмотр и возврат не подтверждают финансовый результат. |
| CHK003 | FR-021/022, plan и quickstart2: старый403 без specific reason даёт только общий отказ начала; недоступное продление не выводится из одного HTTP. |
| CHK004 | Plan ограничивает fixed recurring_not_available ответом403/error/forbidden с точным известным описанием; показ подсказки дополнительно требует HTTP403 и snapshot recurring_consent is True. Quickstart1/2 перечисляет соседние/malformed/nonobject/False ответы. |
| CHK005 | FR-023 запрещает полное тело, описание, request IDs/контакты/секреты; plan допускает только фиксированный признак при сохранении. Quickstart1 требует синтетические маркеры утечки и отказ от произвольных reason. |
| CHK006 | FR-022/SC-009, plan и quickstart3: существующий retry URL/cycle, ручной False, свежие итог/оферта и явный start; нет automatic POST, переключения режима, изменения immutable snapshot или повторного списания. |
| CHK007 | FR-019/020 остаются действующими; plan сохраняет state/dispatch/bind/idempotency/promo/budget; FR-011 сохраняет CSRF/пространство/владельца/цену. Quickstart2/3 отдельно запрещает возрождение expiredpromo и старогоquote. |
| CHK008 | FR-021/023/SC-009 плюс исправленные plan/quickstart: bound/unknown/manual не получают новый creation-rejection путь; неопределённость требует прежней проверки без новой оплаты; достоверная провайдерная отмена сохраняет существующую безопасную возможность повторить. |
| CHK009 | Quickstart1–4 задаёт adapter/state/HTTP матрицу, настоящую Chromium/WebKit форму, ширины320/1280, клавиатуру, JS-off и три независимых flow/security/browser обзора. FR-012 сохраняет200%/темы/доступность. |
| CHK010 | Clarify/addendum и research прямо отделяют внешнее подключение автоплатежей и реальные деньги; plan/quickstart4 требуют новый точный PR SHA, обязательные checks/common validator, frozenFull, CDdry-run/execute, runtime/publication. T011/T012/F278 не закрываются этим результатом. |

## Перепроверка остальных активных пунктов

Все прежние отметки перечитаны и оценены по текущим документам; историческое `[x]` само не принято как доказательство.

| Чеклист и пункты | Актуальные основания |
| --- | --- |
| requirements, все8 | SpecUS1–4/FR001–023/SC001–009, Assumptions/Clarifications; plan содержит технический подход отдельно; human/финансовая/конверсионная готовность не обещается. |
| ux-paymentCHK001/002 | FR001/002 и таблица экранов contracts/payment-journey; одно главное действие и вторичные подробности. |
| ux-paymentCHK003/004 | FR003/007/019, US1 и постоянно видимые сведения contracts: полная сумма/срок/режим, правдивые скидка и trial/paid. |
| ux-paymentCHK005/006 | FR006/007, US2, storage/purchase contract: общий объём, оплаченные периоды, выбор без списания и карта разделены. |
| ux-paymentCHK007/008 | FR009/011/021/023, EdgeCases и состояния contract: unknown не становится отказом/успехом; реальные отказ/невыданный доступ не скрыты. |
| ux-paymentCHK009/010 | US3/4, FR010/011 и invoice/account/renewal contract: существующий безопасный возврат/повтор, годовой цикл, receipt, отмена сохраняет доступ. |
| ux-paymentCHK011/012 | FR008/011 и plan/native contract: узкие method/origin/route правила и прежние финансовые guards. Provider-rejection не расширяет native policy. |
| ux-paymentCHK013/014 | FR012/SC002, quickstart/browser matrix и contract визуальной приёмки:320/200%/фокус/темы и метод уменьшения текста без удаления условий. |
| ux-paymentCHK015/016 | FR014–016/SC004–006, research реестр/границы и quickstart: источники/опровержения/три независимых обзора отделены от людей и конверсии. |
| ux-paymentCHK017/018 | FR011, constitutionIII/VII, plan ConstitutionCheck, quickstartcloseout; приватность/активы и F278/Dev/CI/release разделены. |
| promo-presentationCHK001/002 | Дополнение spec2026-09-30, planT014/015 и tasksT014: период принадлежит сохранённому счёту, unknown не выдумывает месяц. |
| promo-presentationCHK003 | FR003/004/011, specdisplay supplement и T015: непроверенные предложения не рекламируются, ввод известного кода сохраняется. |
| promo-presentationCHK004/005/006 | Историческая неизменностьT014/015 явно отделена от FR017–020/021–023; plan и quickstart сохраняют eligibility/price/receipt/idempotency и синтетические history/apply/cycle/remove проверки, отдельные gates/приватность. |
| promo-refreshCHK001/002/003 | FR017/018/SC007, US1AC5/6: bounded48,300с, дваrefresh/return/cycle, свежая проверка и понятный отказ без ошибочной оплаты. |
| promo-refreshCHK004/005/006/007 | FR011/018–020, plan/data-model: подписанные verifieduser/workspace/session, rejectcorrupt/expired/foreign/legacy/missing, offerunchecked, previewno-money, clear/replace/expiry, узкийcookie и код внеURL/JS/logs. |
| promo-refreshCHK008/009 | FR015–018, quickstart настоящейDOM submit→303/refresh и security; tasksT016–019/историческиеT014/015, отдельныйcandidate, T011/012/F278/конверсия не подменены. |
| optional-renewalCHK001/002 | FR019/SC008/US1AC7–9: optionalchecked/defaultTrue, offerrequired/unchecked; False оплачиваетmonth/year, допустимую скидку, безnewcard/recurring. |
| optional-renewalCHK003/004 | FR003/012/020, plan/data-model/contract: bool предпочтение bounded by metauser/workspace/session, fallback, не offer; OFF summary/keyboard/320/200%. |
| optional-renewalCHK005/006/007 | Plan/commoncreator и entitlements, data-model/contract: actual strictbool, provider saveflag, no unexpectedcardpersist приFalse, immutablekey/snapshot и поздниеcancel/owner/duplicate guards. |
| optional-renewalCHK008/009/010 | FR011/SC008 и quickstart: свежая оферта/quote/CSRF/tenant/owner/paidremainder/receipt/provider success, no-money preview; tasksT020–022 завершены только по собственным evidence, три обзора/новыйexactSHA; T011/012/F278 остаются открытыми. |

## Перечитанные итоги и границы

| Файл | checked | unchecked |
| --- | ---: | ---: |
| requirements.md | 8 | 0 |
| ux-payment.md | 18 | 0 |
| promo-presentation.md | 6 | 0 |
| promo-refresh.md | 9 | 0 |
| optional-renewal.md | 10 | 0 |
| provider-rejection.md | 10 | 0 |
| Все активные | **61** | **0** |
| Reviewer-owned без встроенного requirements | **53** | **0** |

Неподтверждённых пунктов качества требований0. Для нового среза tasks ещё не сгенерированы: прочитанные T001–T022 являются историческими и не считаются готовым планом нового кода. Обязательна повторная сверка после окончательных T023–T025/analyze. Код, syntheticPASS, CI, выпуск, доступность магазина для liveFalse, подключениеRecurring, реальный чек/банк/возврат, GRAFDev и5людей этим отчётом не приняты. Рецензент не отправлял платежи или обращения провайдеру и не менял GitHub/commits/releases/deployments. Изменены только reviewer-owned provider-rejection.md и этот отдельный отчёт.

## Повторная сверка после генерации T023–T025

Окончательные три задачи перечитаны после первичного независимого PASS. Требования по-прежнему PASS: FR-021/022/023/SC-009 покрыты T023 и полной восстановительной/браузерной матрицей T024; FR-011/012/015 и отдельный выпуск покрыты T024/T025. Зависимости последовательны, уникальные task IDs подтверждены; отсутствуют ложные [P] или завершённые отметки будущих действий. Три production-файла принадлежат root, adapter/recovery/HTTP тесты — отдельному исполнителю, browser harness — отдельному исполнителю. Открытые T011/T012/F278/umbrella сохраняются. Другие чеклисты перечитаны: все61/0, reviewer-owned53/0, новый10/0; изменять старые отметки не потребовалось.

Снимок документов на этой сверке (SHA-256):

| Документ | SHA-256 |
| --- | --- |
| spec.md | `9bbcb49dab73e8bcf78f257f9ee08a1958ef090b55abe7d81393b6a145dd66d4` |
| plan.md | `ff18542fb5d27fe213e4a1d0cb56db7b41fe36d17cffb08bfc063454b09a76c6` |
| tasks.md | `28f7dafb0e04c7c5a6e2f3742352b5de20aee13f9c24b6948bfbd47ea30abd8b` |
| quickstart.md | `7801b112e5c9d54ac9d72ee97d0ef10be2e77dc8cd98c7cb0d0c780e27946148` |
| research.md | `a839431250e59b1fb0c7b549c83a6b7bf16e8f0bb4567cd0320f79f94592ef3f` |

`git diff --check` PASS. На момент этой записи analysis/issue-sync артефакты ещё готовятся другими владельцами; отсутствие их локального документа не подменяется устным PASS. До кода требуется их отдельное завершение.

Последующая независимая сверка: прочитан сохранённый `analyze-provider-rejection.md` после генерации задач. Его карта FR-021–023/SC-009 → T023/T024, выпуск → T025 соответствует перечитанным задачам и требованиям. CRITICAL0/HIGH0, дубли/несвязанные задачи0 подтверждены собственным чтением; исправленных неоднозначностей больше нет. **Окончательный requirements/consistency gate PASS**, чеклисты снова перечитаны61/0. Canon issue sync остаётся отдельным обязательным действием владельца GitHub перед кодом; это ревью его не заменяет.
