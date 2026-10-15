# Независимая проверка требований: необязательное автопродление F280

Дата: 2026-10-01. Рецензент: `optional_renewal_requirements`. Рабочая ветка: `codex/280-payment-optional-renewal`. Проверяется качество требований перед реализацией T020–T022, а не работоспособность опубликованного кода.

**Результат: PASS требований; блокирующих неподтверждённых пунктов 0.** Прочитаны все пять checklist целиком, актуальные spec/plan/data-model/contracts/quickstart, задачи и исследовательское решение. Исторические `[x]`, результаты прошлых тестов и выпусков не использованы как доказательство новой реализации. Допуск позволяет завершить генерацию задач и провести analyze/issue sync. До кода эти отдельные условия остаются обязательными.

## Новые требования: отдельное основание каждого пункта

| Пункт | Основание текущих документов | Решение |
| --- | --- | --- |
| CHK001 | Spec FR-019, US1/AC4 и уточнение US1/AC7–9; plan «Необязательное продление»; contract: offer unchecked/required, recurring checked/not-required. Новое явное решение заменяет прежние ожидания двух пустых галочек, исторические версии не переписываются. | Подтверждён |
| CHK002 | FR-019 и SC-008, data-model «Выбор продления»: month/year × скидка/без скидки, один оплаченный период, save_payment_method=False, recurring_allowed=False. Quickstart пункт2 отдельно покрывает уже активное продление. | Подтверждён |
| CHK003 | FR-020 и его явное ограничение; plan задаёт sessionStorage только bool по существующим meta UUID user/workspace/session, до конца браузерной сессии. Apply/error/remove/cycle/reload/303/409 не меняют явный False. Missing meta/storage failure/noJS ограничены текущим документом; оферта не восстанавливается. | Подтверждён |
| CHK004 | FR-003/012/019, contract «Постоянно видимые сведения» и «Необязательное продление»: OFF не обещает списание, следующая обычная цена видна как цена периода. Базовый HTML условный «При автопродлении», JS скрывает дату автоматического списания. Клавиатура/экранный диктор, 320px/200%, итог/срок/скидка заданы. | Подтверждён |
| CHK005 | Plan130, data-model28 и contract63: actual денежный POST хранится в request+invoice; creator принимает именно bool, отсутствующие/строковые/числовые снимки отвергает. Визуальное предпочтение не разрешает платеж и не подменяет authority/quote/offer. | Подтверждён |
| CHK006 | FR-019/SC-008, plan130, quickstart149: новая карта сохраняется только при consent is True; неожиданная saved card при False не записывается; выдача периода не зависит от разрешения повторных списаний. | Подтверждён |
| CHK007 | FR-020, plan130/132, contract63, quickstart148–151: recovery сохраняет исходный bool и ключ. Новая обычная вкладка без opener начинает True; стандартное клонирование sessionStorage через opener названо ограничением. Поздняя отмена/authority drift/owner/duplicate не включают продление, прежний paid remainder сохранён. | Подтверждён |
| CHK008 | FR-011/018/019/020, contract63, quickstart148–151: offer=true обязателен, preview без финансовых записей, свежий серверный quote, verified receipt, CSRF/owner/tenant/provider confirmation и прежняя защита повторов обязательны. Missing recurring формы — False; invalid не становится True. | Подтверждён |
| CHK009 | Проект T020 RED/код → T021 реальные браузеры/три независимых обзора/converge → T022 новый exact-SHA PR/Full/CD/runtime/release; quickstart146–153. Анализ и issue sync перед кодом обязательны, старый frozen кандидат и macOS байты не меняются. | Подтверждён |
| CHK010 | Spec206, tasks Phase9/T022, quickstart153: T011/T012 и финансовая F278 открыты отдельно; новые tests/agent PASS не заменяют людей, реальную оплату, чек/зачисление/возврат и измерение конверсии. Старые доказательства помечены историческими. | Подтверждён |

Никакого TTL, cookie или серверного хранения предпочтения продления не требуется. Временный подписанный promo draft остаётся отдельным прежним договором TTL300. Клиентский bool служит удобству оформления; только фактическая отправка денежной формы и авторитетные снимки задают оплачиваемый режим. Без JavaScript явное снятие галочки отправляет отсутствие поля, трактуемое сервером как False, поэтому разовая оплата не зависит от sessionStorage.

## Повторная оценка остальных действующих checklist

Каждый пункт оценён по текущим артефактам; прежняя отметка сама по себе не является основанием. Подтверждения относятся только к полноте/ясности требований. Текущий срез явно заменяет старое правило пустых обеих галочек, сохраняя обязательную непринятую оферту.

| Checklist / пункт | Текущее основание |
| --- | --- |
| ux-payment CHK001 | FR-001 и таблица экранов/смежные входы contract |
| ux-payment CHK002 | FR-002 и главное действие для каждой строки contract |
| ux-payment CHK003 | FR-003/019; contract различает условную будущую цену и фактическое автоматическое списание, обязательные условия на виду |
| ux-payment CHK004 | US1/AC3, FR-005, plan и таблица тарифов/скидок contract |
| ux-payment CHK005 | US2, FR-006, contract storage timeline/paid remainder |
| ux-payment CHK006 | FR-007/019/020; data-model разделяет визуальный выбор, способ оплаты и финансовый снимок |
| ux-payment CHK007 | US3, FR-009/011/020, contract Pending/unknown/recovery и immutable key |
| ux-payment CHK008 | Contract Succeeded_refused/owner_changed/service_gap/storage_period_elapsed и Edge Cases |
| ux-payment CHK009 | Contract receipt/account next и status recovery; FR-019 сохраняет год/контакт и отдельный режим продления |
| ux-payment CHK010 | US4/AC2, FR-010/020, contract cancel и quickstart поздней отмены |
| ux-payment CHK011 | FR-011, contract63 и plan130: CSRF/role/workspace/offer/quote/authority/key сохранены |
| ux-payment CHK012 | Contract «Нативная навигация»: четыре точных POST, trusted origin/method, sibling запрет; новый срез её не меняет |
| ux-payment CHK013 | FR-012 и contract/quickstart: темы/320/200%, keyboard/focus/status |
| ux-payment CHK014 | SC-002 и contract визуальной приёмки: видимые слова при неизменных существенных условиях, не конверсия |
| ux-payment CHK015 | Research D01–D08 и реестр S01–S12 содержат источники, опровержения, применимость и отсутствие доказанной конверсии GRAF |
| ux-payment CHK016 | FR-015/016, SC-004/005/006, T021 и открытая T012: независимые обзоры отдельно от людей/метрик |
| ux-payment CHK017 | FR-011, plan Constitution/Constraints, research limits: синтетические данные и никаких новых активов/аналитики |
| ux-payment CHK018 | Spec206, plan134, T011/T012/T022 и quickstart153 разделяют Dev, локальные/PR/release/runtime и внешние доказательства |
| promo-presentation CHK001 | Spec уточнение T014/T015: история читает период совершённой покупки; plan supplement и T014 |
| promo-presentation CHK002 | Spec/plan T014 и quickstart T014/T015: неизвестный период не выдумывается |
| promo-presentation CHK003 | Spec FR-003/004/011 и T015: неподтверждённый список убран, известный код проверяется сервером |
| promo-presentation CHK004 | Явное примечание checklist ограничивает исторической T014/T015; новое FR-019/020 отдельно изменяет выбор продления. Цена/eligibility/TTL/path/provider/receipt/key прежние |
| promo-presentation CHK005 | Quickstart T014/T015 и сохранённая матрица code→month/year→remove, изменившаяся кампания/неизвестный период |
| promo-presentation CHK006 | FR-011/015/016, T011/T012/T022, quickstart153: роли/приватность/синтетический провайдер и отдельный выпуск |
| promo-refresh CHK001 | FR-017, US1/AC5–6, plan модель/quickstart1: code/period после Apply/двух reload/возврата |
| promo-refresh CHK002 | FR-017/018, data-model draft, quickstart7: ровно300с, чтение и смена периода срок не продлевают |
| promo-refresh CHK003 | FR-017, plan bounded encoded/HMAC ввод, quickstart3: ≤48, malformed/nonASCII/control, ошибка и запрет оплаты |
| promo-refresh CHK004 | FR-018, plan binding, quickstart6: три проверенных границы, tamper/rename/missing session/key/legacy отказ |
| promo-refresh CHK005 | FR-003/011/018/019/020, plan общий renderer, quickstart: свежий quote/eligibility, offer unchecked, визуальный bool независим от денег |
| promo-refresh CHK006 | FR-018, data-model transitions, quickstart5–7: empty/remove/replacement/expiry/foreign/operation различены |
| promo-refresh CHK007 | FR-011/018, plan/data-model draft: HttpOnly/SameSite/Secure/path, код не в URL/JS/logs, без новых зависимостей |
| promo-refresh CHK008 | Quickstart настоящих HTTP/DOM и границ, FR-015, T021/T022: новые current review/выпуск, старый PASS не наследуется |
| promo-refresh CHK009 | Spec historical T014/T015 и уточнение206, tasks Phase9: lifetime расширен отдельно, T011/T012/F278 открыты, авторизация владельца записана |
| requirements 1 | Spec описывает продуктовые действия/границы; алгоритм, ключ sessionStorage и strict-bool caller находятся в plan/data-model/contract |
| requirements 2 | US1–US4, FR-019/020 и Assumptions задают ценность и объём |
| requirements 3 | Сценарии, требования, критерии, зависимости и clarify заполнены, одноразовая покупка проверяется независимо |
| requirements 4 | Spec204–210: прямое решение пользователя, новые уточнения0, fallback и вкладки определены |
| requirements 5 | SC-004–008, T021/T022, T012: код/люди/метрики различены, month/year×bool и запреты объективны |
| requirements 6 | Edge Cases, FR-009/011/012/020, contract и quickstart покрывают ошибки/recovery/a11y/security |
| requirements 7 | Assumptions, spec206 и quickstart153 явно называют F278 и пределы |
| requirements 8 | FR-016/SC-005/006 и Assumptions не гарантируют покупки каждого посетителя |

Старая фраза «согласия пусты» в хронологии завершённых T016–T019 относится к предыдущему срезу. Spec206 и tasks Phase9 явно ограничивают её исторической версией. Текущее правило — оферта непринята, выбор продления по FR-019/020. Это не противоречие действующего договора. CHK004 promo-presentation аналогично имеет явную историческую область.

## Конституция и условия продолжения

Прочитана Constitution7.1.0 целиком; применимы §II/III/VI/VII, независимый reviewer gate и metadata-only proof. Прочитаны guidance index, spec-kit-flow целиком, product-gates целиком, применимые release-and-validation разделы Local/Validation/Production gate/Closeout/Release Notes/Git Safety/Evidence Safety; baseline PRD обещания/доступность и current-product-status текущая шапка/биллинг. Старые записи общего статуса не используются как свежая production truth.

Выбранная ветка и `.specify/feature.json` соответствуют F280. Конституция не требует предвыбранного или непредвыбранного разрешения оплаты; отдельная оферта и видимый обратимый выбор отвечают текущему явному решению пользователя. Capture/AI/third-party provenance не расширяются. Существующие paid remainder, receipt и сверка не ослаблены требованиями. Нарушений конституции по изученному дизайну не найдено.

Следующие обязательные условия: окончательная генерация T020–T022, analyze, deduplicated issue sync, RED→GREEN, три current независимых обзора и converge, новый exact-SHA CI/Full/CD/runtime/release. Они пока не доказаны этим отчётом и не разрешают назвать исправление готовым.

## Перечитывание и итоги

После изменения рецензент повторно прочитал все пять checklist. Итоговые счётчики:

| Checklist | Checked | Unchecked |
| --- | ---: | ---: |
| optional-renewal.md | 10 | 0 |
| ux-payment.md | 18 | 0 |
| promo-presentation.md | 6 | 0 |
| promo-refresh.md | 9 | 0 |
| requirements.md (встроенный) | 8 | 0 |
| Всего | 51 | 0 |

Reviewer-owned всего43/0; built-in8/0. Неподтверждённых пунктов требований0. Реализацию, коммиты, GitHub state, release/deploy, реальную оплату и человеческую приёмку рецензент не проверял и не менял. Изменены только пять checklist и этот отдельный отчёт.

## Снимок прочитанных артефактов

SHA-256 фиксирует именно документы этого требования; повторные изменения требуют оценки влияния. Ни один hash не является доказательством выполнения кода.

- `spec.md`: `5c62bbe5be4b6cb38c3efea38431a65bf23726565f1c61fb40df015ac9dcbaa3`
- `plan.md`: `3ab356ec1e96135c6b4c9e5095a668fa6e60ed437b8ac0f2fe4b7d846353bcac`
- `data-model.md`: `f49d566ed31da1fe56a2e32be380bc65a7a7d90e13e16ca9fbfc5f4de4546d68`
- `contracts/payment-journey.md`: `95b94fa5373cf00151704c8ec5a865f35a41bb290bca4d409e6d0698d4b217b3`
- `quickstart.md`: `697b785ed5acbbebc7140479df85226de3762d9fe356fbe5b6c93cd34179f53c`
- `tasks.md`: `63ff03c10f812adba149c544f1b35ce355f0519e2389ae0029188776a8d0760e`
- `research.md`: `ca8cee6867807d2f50faba374a2eec59137912825e322f9ce8fac420fb6ff3a4`


## Повторный текущий обзор после уточнения FR-003 и namespace

Дата: 2026-10-01. Независимый рецензент: `optional_renewal_requirements_final`. Прочитаны все пять checklist, spec/plan/tasks/data-model/contract/quickstart, исследовательские решения, Constitution7.1.0 и применимые правила Spec Kit/product/release. Ветка и указатель F280 проверены. Исторический обзор выше сохранён как запись прежних документов; текущий допуск определяется этим дополнением.

**Требования PASS; неподтверждённых пунктов 0.** Каждый пункт снова оценён по действующему договору, а не по прежней отметке или сообщению автора. Таблица оснований выше остаётся применимой с указанными ниже уточнениями:

- Optional-renewal CHK001–003 и CHK005–010: FR-019/020/SC-008, действующие data-model, plan:130–134, contract:61–63, quickstart:146–153 и окончательные T020–T022 дают те же явные default/False/boundary/authority/recovery/security/release требования. Исходный tasks hash изменился после окончательной генерации: последовательность и критерии конкретно заданы, а завершение задач не выводится из этого допуска.
- Optional-renewal CHK004 и ux-payment CHK003: актуальный FR-003 и первый раздел контракта явно различают три ситуации. В checkout одного периода без продления видны текущий итог, срок и отсутствие будущего автоматического списания; сумма и дата несуществующего списания не обязательны. При включённом продлении видны будущая полная сумма и реальная дата/правило первой попытки. В управлении подпиской и покупке хранения условная цена следующего периода сохранена. Базовый HTML без JavaScript имеет условные подписи. Предыдущая строка основания CHK004 о видимой цене следующего периода не относится к разовому checkout в текущей версии.
- Reviewer-owned вопрос ux-payment CHK003 уточнён по этому действующему FR-003; это устраняет старое безусловное «всегда» в самом списке проверки и не меняет продуктовый договор. CHK001/002/004–018 перечитаны отдельно: матрица экранов, скидки/объём, recovery/receipt/route policy, доступность, измеримость/исследование/privacy и границы T011/T012/F278 остаются определены.
- Plan:132 задаёт фактический namespace `graf-checkout-renewal:<user>:<workspace>:<session>`. Он соответствует data-model:30 и контракту scoped visual preference. Название ключа не становится финансовой авторизацией; снимок денег и подписанный promo draft остаются отдельными.
- Promo-presentation CHK001–006: сохранённые периоды истории/unknown, запрет непроверенного предложения, синтетическая матрица и отдельные финансовые ворота подтверждены текущими требованиями; неизменность согласий CHK004 имеет явно историческую область T014/T015.
- Promo-refresh CHK001–009: code/cycle/TTL300/binding/format/explicit remove/authority/privacy и реальные browser требования не изменяются новым bool предпочтением. FR-003/019/020 условного будущего списания совместимы с новым CHK005; принятие оферты никогда не переносится.
- Built-in requirements1–8: действующие пользовательские сценарии, проверяемые FR/SC, обязательное clarify и открытые границы дают доказательства всех восьми критериев. Гарантия оплаты каждым человеком или доказанный рост конверсии по-прежнему не заявляются.

Не найдено противоречий действующих требований, неразрешённых уточнений или конституционных нарушений. Несовпадения исторических веток/пустых обеих галочек в закрытых срезах явно ограничены хронологией; текущая Phase9 и FR-019/020 имеют явный приоритет. Снятая галочка позволяет обычную оплату без JavaScript; сохранение через навигацию ограничено документированным fallback. Рецензент не проверял реализацию, результаты тестов, финансовые записи, CI или production и не изменял их. Полный выпуск и три обзора кода остаются отдельными условиями.

После изменения перечитаны все пять checklist: optional-renewal10/0, ux-payment18/0, promo-presentation6/0, promo-refresh9/0, requirements8/0. **Reviewer-owned43/0; общий итог51/0.** Изменены только разрешённые checklist и этот отчёт. Неподтверждённых требований нет; root должен обновить analyze для этих текущих документов.

SHA-256 текущих прочитанных артефактов:

- `spec.md`: `d0e028ca63f1a9507dccf80e7b0584bce03e344aa6ff505dc9e50a3e98ce898d`
- `plan.md`: `7f9fa8bce8b5170647eccf7f358890dccde36a707364aae38c56b0e1712b0309`
- `tasks.md`: `22599a3f882888dd11594df30b0cdb54860d164d574f660f6e8ad870f89af926`
- `contracts/payment-journey.md`: `18e874d0549bf5102b701b222e4a6a4f1ebcfccfaca98e32c827d6d42bae220c`
- `data-model.md`: `f49d566ed31da1fe56a2e32be380bc65a7a7d90e13e16ca9fbfc5f4de4546d68`
- `quickstart.md`: `697b785ed5acbbebc7140479df85226de3762d9fe356fbe5b6c93cd34179f53c`
- `research.md`: `ca8cee6867807d2f50faba374a2eec59137912825e322f9ce8fac420fb6ff3a4`
