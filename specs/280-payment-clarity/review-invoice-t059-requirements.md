# F280 T059 — независимая проверка требований invoice

2026-10-04. Reviewer `/root/sdd_supplement`; полоса `high-risk-product`, продолжение FR050/052/SC016/017. Ownership только `checklists/invoice-consistency.md` и этот новый отчет. Код/тесты/canonical/чужие reports/Git/GitHub/commits/releases/deploy не менялись; матрицы reviewer не запускал.

**REQUIREMENTS PASS — 14 checked, 0 unchecked.** Незакрытых CRITICAL/HIGH/исправимых MEDIUM пробелов качества требований нет. Это допуск требований до минимальной реализации T059; code/source/visual/CI/production допуск не следует из отметок.

## Прочитанные окончательные требования

Перечитаны actual T059 spec403–409, plan280 и final supplement, окончательная task T059 с `(Issue #7530)`, contract156 и final supplement, quickstart316 и final supplement, scoped T059 analyze60 и thirdcopy уточнение. Invoice analyze/review прежнего среза прочитаны как история; действующий T059 scoped analyze расположен в `analyze-subscription-clarity.md`. Проверены все четырнадцать checklist пунктов, FR046–052/SC016–017 и прежние clarify/ownership/геометрия720/research/data-model/quickstart. Применены правила `$speckit-checklist` качества требований и reviewer-owned gate, guidance index/spec-kit-flow/product-gates/constitutionVI/VII. Текущий HEAD до записи `3c18962a24954a55e60feb9a7c6c66f6b477eabb`; заключение связано с рабочими байтами ниже, не с завершенностью этого SHA.

T059 сохраняет существующую F278 quiet форму `POST /billing/checkout/status/{safe_number}/refresh?return_to=invoice` только по настоящему can_refresh_receipt, с existing CSRF/owner/scope/rate/receipt_only guards. Это явное наблюдение уже оплаченного чека, не новое списание, возврат или повторная выдача доступа. GET страницы/локальные раскрытия провайдера и деньги не вызывают; false/default/unavailable contexts форму не получают. Поэтому support contract должен запрещать другие денежные формы и точно проверять единственную разрешенную nonfinancial receipt форму, endpoint, CSRF и условность, сохраняя privacy/URL/negative guards. Требования не разрешают удалять законную проверку чека ради устаревшего blanket `<form` запрета.

Прочитанный `f280-invoice-t059-red.log` содержит3 failed/80 passed: support guard, invoice copy и subscription copy. При первоначальном чтении scope описывал только два отказа; CHK014 находился HOLD до final clarify. Root дополнил все шесть canonical документов: одна замена «Проверить платёж»→«Проверить платеж» в subscription template общей локальной invoice ветки принадлежит root, peer адаптирует три точных CJS selector literals. URL/условия/порядок/контролы/денежные semantics/assertions неизменны; новая feature или user decision не нужна. После последнего сигнала root перечитаны еще раз spec407/plan280/task311/analyze60: они прямо описывают три compatibility исправления, root/peer ownership и final issue #7530. Пробела scope больше нет.

Последовательность causal RED→полные support/UI/copy GREEN→focused invoice+F278 receipt/permission/service-gap DB→combined Chromium/WebKit/NoJS→distinct source/visual reviews→actual merge/base equivalence/newexactPRCI→один frozen release определена. Проверки не ослабляют assertions/лимиты; metadata-only смена базы требует доказанного совпадения байтов, не автоматического переноса evidence. Будущие результаты не названы PASS.

## Повторная оценка четырнадцати пунктов

| Пункт | Основания | Решение |
|---|---|---|
| CHK001 | FR046/spec361; contract143; T059spec405 | PASS: purchase facts/результат/срок/чек на виду, история вторично, одно доминирующее действие; F278 receipt refresh quiet. |
| CHK002 | FR046/052; plan259/269; research275 | PASS: общая ширина720/геометрия, независимое владение и собственные денежные условия. T059 геометрию не меняет. |
| CHK003 | FR047/048; spec362/363; contract143 | PASS: created отличен от подтверждения денег/оплаченных границ и текущей активности. |
| CHK004 | FR047/048; acceptance2; data-model38–41; quickstart303/305 | PASS: короткие/точные viewer-local сроки, неизвестные данные и несколько storage intervals без потери. |
| CHK005 | FR048; acceptance4/7; quickstart303/305 | PASS: безопасный номер/copy, действительная ненулевая скидка, маскирование и privacy прежнего payer. T059 их не расширяет. |
| CHK006 | FR049; plan263; contract145; acceptance5 | PASS: question/refund разные проверенные mailto, не отправляют/не возвращают деньги, безопасная fallback помощь. |
| CHK007 | FR050; T059spec405/407; contract145/156; taskT059; quickstart316 | PASS: состояния/права/URL правдивы; единственный разрешенный receipt-only endpoint с CSRF и условным can_refresh_receipt, negative false/default/unavailable и отсутствие прочих денежных forms явно определены. |
| CHK008 | FR048/051/FR031–038; contract143/147; T059spec405 | PASS: service_gap/ожидание/recovery/финансовая истина вне сведений. Receipt observation не подтверждает новый платеж/доступ и сохраняет paid truth. |
| CHK009 | clarify353–356; FR019/020; contract149; T059spec407 | PASS: предвыбор везде и continuous explicit choice сохранены; rejected off не вводится. |
| CHK010 | FR012/052; acceptance6; quickstart303/316/final supplement | PASS: native controls/focus/keyboard/themes320/200%/NoJS; final combined browsers после адаптации точных selectors, без ослабления assertions. |
| CHK011 | FR014/052; research274–280/268; constitutionVII | PASS: собственный код/ресурсы, приватные reference материалы вне git, честные пределы Krisp/рекомендаций. Новых активов T059 нет. |
| CHK012 | SC016/017/acceptance1–7; T059tasks#7530/quickstart316/analyze60+supplement | PASS: read counts/provider0 и полный state coverage измеримы; compatibility task4refs/1task и текущие RED→GREEN проверки определены. |
| CHK013 | SC017; quickstart307/309/316; T055/056; final supplement | PASS: synthetic/server/live/installed/financial/human различены, общий frozen release/newCI и dependency merge доказательства отдельны. |
| CHK014 | scope386/clarify355; T059spec405/407/409; plan/task/contract/quickstart/analyze final supplement | PASS после уточнения: legitimate merged F278 наблюдение сохранено, новых money rights/models нет; root mechanical1glyph и peer3selectors имеют точную ownership/scope без смены поведения. |

Все пункты проверены повторно, прежние `[x]` не использованы как самостоятельное доказательство. CHK007/014 уточнены как вопросы полноты требований; история checklist сохранена. Реализация, реальные платежи/provider/mail/refund, Dev, SC005/006/F278 human/outcome или production не приняты этой проверкой.

## SHA-256 окончательных документов

| Путь | SHA-256 |
|---|---|
| `specs/280-payment-clarity/spec.md` | `2c447b13d08064d77b9fd7657252cb9c96438bed9e8c763f9e8520f3230883e5` |
| `specs/280-payment-clarity/plan.md` | `5f75a2932b18aa4a2083d847815033ae45408ce3f8e3c47f8bfd30a2b692119b` |
| `specs/280-payment-clarity/tasks.md` | `505d8d8d5d54c6346cb2d0091dc61d0047c35e1e528afffc55271d15a5d7ead8` |
| `specs/280-payment-clarity/contracts/payment-journey.md` | `48b6d3f514f16c32b9c3e283a1c55a9c5d2405bc1358bb1c1b257c70d6d6cdf1` |
| `specs/280-payment-clarity/quickstart.md` | `d5b0de1efeb1382f68ffbd4ae75df649c40141a8ed6c7a46d8ae5bec4824ae02` |
| `specs/280-payment-clarity/analyze-subscription-clarity.md` | `a032d94f7314883979fd6d7b7ff7e7ffe42cd4a274f75010b8e0575f9c3ddda9` |
| `specs/280-payment-clarity/research.md` | `1a1127fd2e5109091facf51f4ee35be19728ef10ba43b175fea55a13d62dd484` |
| `specs/280-payment-clarity/data-model.md` | `ee98852e601068856101743d54c5c150f35529a5f3fe4fcc06002a061c6c7edd` |
| `.specify/memory/constitution.md` | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |

После записи reviewer перечитал итоговый checklist: **actual14 checked/0 unchecked**, и новый отчет; все девять SHA-256 повторно совпали, `git diff --check` двух reviewer файлов прошел. ROOT canonical/issues/analyze внешние действия принадлежат координатору. REQUIREMENTS PASS снимает только gate полноты требований; будущие implementation/source/visual/exactSHA/base/merge/release/live должны получить собственные доказательства.
