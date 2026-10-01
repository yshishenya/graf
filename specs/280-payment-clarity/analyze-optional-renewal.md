# F280 — анализ дополнения необязательного автопродления

Дата: 2026-10-01. Ветка `codex/280-payment-optional-renewal`. Lane `high-risk-product`; выпуск отдельно `release-deploy`. Анализ выполнен после независимого requirements PASS и окончательной генерации T020–T022. Это проверка согласованности требований, не приёмка кода или production.

## Допуск и источники

`check-prerequisites.sh --json --paths-only`, `setup-plan.sh --json` (существующий план сохранён), `setup-tasks.sh --json`, затем актуальный `check-prerequisites.sh --json --require-tasks --include-tasks` подтвердили активную F280. Установленный prerequisite script не поддерживает upstream `--require-spec`: первоначальный вызов отвергнут; вместо обхода использован supported require-tasks и явно прочитан существующий spec.md. Feature identity/активная ветка сохранены, номер новой фичи не выделялся.

Использованы specify → clarify → plan → checklist → tasks → analyze для дополнения существующего среза. Clarify: новых вопросов0, прямое решение пользователя зафиксировано в spec; новые FR-019/020 заменяют старое ожидание пустых обеих галочек. Hooks прочитаны из extensions.yml: commit hooks disabled, optional agent-context skip (стабильный router AGENTS не меняется), existing-feature branch reservation reused. Issue sync canon ensure/validate и реализация принадлежат основному агенту. Converge не запускался до реализации T020/T021 и не объявлен PASS.

Независимый отчёт [review-optional-renewal-requirements.md](review-optional-renewal-requirements.md): optional10/0, ux18/0, presentation6/0, promo-refresh9/0, built-in8/0; reviewer-owned43/0, общий51/0. Все чеклисты перечитаны рецензентом; автор дополнения не отмечал их. Следующее изменение tasks — только подтверждение окончательной генерации после этого gate, смысл/объём трёх задач не менялся.

## Согласованность и покрытие

| Источник | План/договор | Задача | Результат анализа |
| --- | --- | --- | --- |
| FR-019, US1/AC4/AC7–AC9 | optional checked recurring, required unchecked offer; False→один период/no new card/no recurring | T020 | Однозначно; actual POST→bool snapshots→provider bool→grant |
| FR-020 | sessionStorage только визуальный bool по существующей тройке meta; отдельные обычные вкладки, отказ storage/noJS ограничены | T020/T021 | Серверные cookie/API не расширяются, TTL300 только прежнему промокоду |
| FR-003/007/010/012 | текущая сумма/срок видны; False OFF, noJS будущая сумма условно «При автопродлении» | T020/T021 | Режим не скрыт, оплата доступна с клавиатуры |
| FR-011, прежние денежные границы | CSRF/owner/tenant/quote/offer/authority/idempotency, paid remainder/receipt/duplicate | T020/T021 | No-save не ослабляет цену/оферту/подтверждение; recovery immutable |
| SC-008, FR-015 | RED/GREEN month/year×modes, FormData missing=False, saved-card surprise, late cancel/owner, браузеры320/1280/JS-off | T020/T021 | Проверяемые критерии; три независимых обзора актуального кода |
| Release gate, FR-016 | новый exact-SHA PR, frozen Full, CD dry-run/execute/runtime/publication; no new macOS bytes | T022 | Старый выпуск не доказательство нового среза; T011/T012/F278 остаются открытыми |

Исторические T001–T019 и отчёты до дополнения не переписаны как новые доказательства. Актуальные нормативные ожидания пустых обеих галочек заменены непредвыбранной офертой и FR-019/020. Предварительный scope не требует framework, нового browser harness или новых таблиц: существующие recovery/entitlements/money-path и promo-refresh/accessibility наборы расширяются. Новые executable tasks ровно3, IDs уникальны, зависимости последовательны, [P] отсутствует из-за общих договоров.

Constitution §II/III/VI/VII и product-gates сверены: capture не меняется; видимое обратимое разрешение и явная отправка обязательной оферты сохранены; код/суммы/credentials не помещаются в browser preference/analytics/evidence; независимый review и release gates обязательны. Неподтверждённых конфликтов конституции не найдено.

## Findings

CRITICAL0 · HIGH0 · MEDIUM0 · LOW0. Неразрешённых уточнений0; новых непокрытых требований0. Порог analyze PASS. Проверки согласованности: новые FR2/SC1 и связанные инварианты FR003/007/010/011/012/015/016, три задачи, 5checklists. Проверка идентификаторов/сохранения T011/T012 и `git diff --check` PASS.

## Снимок артефактов до реализации

- spec.md SHA256: `5c62bbe5be4b6cb38c3efea38431a65bf23726565f1c61fb40df015ac9dcbaa3`
- plan.md SHA256: `3ab356ec1e96135c6b4c9e5095a668fa6e60ed437b8ac0f2fe4b7d846353bcac`
- tasks.md SHA256: `22599a3f882888dd11594df30b0cdb54860d164d574f660f6e8ad870f89af926`

Следующий шаг: canon ensure→issue dedup/sync→canon validate, затем implementation T020. Код/коммиты/GitHub/production автором этого отчёта не менялись. После реализации обязательны T021 и отдельный converge, затем T022; никакой новой опубликованной готовности этим анализом не заявляется.

## Уточнение после независимой трассировки исходников

2026-10-01: исправлены два документальных расхождения, обнаруженные при source review: FR003/contract теперь требуют будущую цену в checkout при включённом продлении; для разовой покупки видны сумма/срок/OFF. Plan использует фактический namespace `graf-checkout-renewal:<user>:<workspace>:<session>`. Эти уточнения перечитаны автором flow/converge; оставшихся расхождений в данном срезе не найдено. Новые задачи не добавлены: ожидаемые окончательные browser receipts/три независимых обзора и новый выпуск уже покрыты T021/T022.

Текущий снимок документов:

- spec.md SHA256: `d0e028ca63f1a9507dccf80e7b0584bce03e344aa6ff505dc9e50a3e98ce898d`
- plan.md SHA256: `7f9fa8bce8b5170647eccf7f358890dccde36a707364aae38c56b0e1712b0309`
- tasks.md SHA256: `22599a3f882888dd11594df30b0cdb54860d164d574f660f6e8ad870f89af926`
- contracts/payment-journey.md SHA256: `18e874d0549bf5102b701b222e4a6a4f1ebcfccfaca98e32c827d6d42bae220c`

**Повторный reviewer-owned requirements review исправленных документов PASS**: новый `optional_renewal_requirements_final` перечитал все пять checklist и действующие артефакты независимо; [текущее дополнение отчёта](review-optional-renewal-requirements.md) фиксирует reviewer-owned43/0, built-in8/0, общий51/0, неподтверждённых требований0. Его текущие spec/plan/tasks/contract hashes совпадают с указанными выше. Ранее agent thread limit препятствовал возобновлению прежнего рецензента; эта техническая преграда преодолена отдельным независимым повторным обзором. Автор анализа не выставлял отметки checklist. Анализ исправленных документов PASS: CRITICAL/HIGH/MEDIUM/LOW0/0/0/0, неразрешённых уточнений0, новых непокрытых требований0. [Scoped converge](converge-optional-renewal.md) отдельно фиксирует код и доказательства выполнения.

Окончательное дополнение после receipts: UI заморожен, contracts69 PASS, accessibility Chromium16/WebKit16 PASS, verified real HTTP/SQL Chromium1 PASS82.45с/WebKit1 PASS173.89с. Три независимых текущих flow/security/browser заключения PASS0 findings, source hashes совпадают. В scoped converge локальный T021 больше не имеет ожидающих доказательств; T022 остаётся открытым выпускным этапом. Первоначальные докодовые формулировки выше сохраняются как хронология. Tasks не менялись этим автором.
