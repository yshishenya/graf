# F280 — сходимость дополнения необязательного автопродления

Дата: 2026-10-01. Lane `high-risk-product`, последующий выпуск `release-deploy`. Ветка `codex/280-payment-optional-renewal`. Независимый scoped обзор после реализации T020; финальная локальная проверка T021 и три независимых заключения подтверждены; T022 не завершён. Данный отчёт не объявляет завершённой F280.

Активная F280 подтверждена supported `check-prerequisites.sh --json --require-tasks --include-tasks`, spec прочитан явно (upstream `--require-spec` этим скриптом не поддерживается). Применена read-only оценка speckit-converge в границах делегированного ownership. before/after_converge hooks отсутствуют. Tasks не изменены.

## Соответствие

| Источник намерения | Код/доказательство | Результат |
| --- | --- | --- |
| FR-019, US1: снятие recurring допускает один месяц/год | Native optional checked recurring + required unchecked offer; Form defaultFalse; actual bool snapshots; initial save flag; entitlement strict True | Реализовано, исходники PASS |
| FR-020: выбор не сбрасывается, UI не авторизует деньги | Scoped tab sessionStorage только bool; init/HTMX/pageshow; immutable snapshots/idempotence | Реализовано; final verified Chromium1 PASS82.45с/WebKit1 PASS173.89с |
| FR-003/007/010/012: понятные сумма/срок/режим | OFF явен, следующая дата скрыта; без JS условная будущая подпись; keyboard/native form | Реализовано; accessibility Chromium16 PASS26.20с/WebKit16 PASS32.82с, contracts69 PASS |
| FR-011: цена/оферта/owner/CSRF/receipt/paid remainder | Общий creator оставляет guard; reconciliation authority/current owner; money-path матрица и no-money preview | Изменённый срез сохраняет инварианты |
| SC-008: оба режима и defensive saved card | Backend49 PASS; HTTP465 PASS/2 stale failures + исправление/return82 PASS; month/year×True/False/omitted, opposite retry, old card/remainder; final real browser→HTTP→SQL | Серверное и браузерное синтетическое доказательство есть |
| FR-015/SC-004, T021 | Три независимых текущих обзора flow/security/browser PASS0 findings; повторный requirements51/0 | Локальная проверка завершена; отметка tasks принадлежит root |
| FR-016, T011/T012/F278 | Человеческое понимание/конверсия/финансовая приёмка | Открыто, синтетические доказательства не заменяют |
| T022 release-deploy | Новый exact-SHA PR/Full/CD/runtime/publication | Открыто, прошлый выпуск не доказывает новый код |

Два предварительных документальных расхождения (безусловная будущая цена и namespace) исправлены; актуальные FR003/contract/plan перечитаны. Новых missing/partial/contradicts/unrequested **в исходниках дополнения:0**, CRITICAL/HIGH/MEDIUM/LOW **0/0/0/0**. Новых исполнительных задач не требуется: оставшиеся выпускные проверки уже точно покрыты T022. Это **source-converged, local validation PASS, release pending**, а не полный converge PASS всех tasks. Отметки T020–T022 и review-owned checklist принадлежат основному агенту/рецензентам.

Проверено: FR019/020, связанная SC008, семь инвариантов FR003/007/010/011/012/015/016, три новых задачи, решения plan: existing source/no new tables, native form, scoped bool/no API, JS/noJS fallback, idempotence/snapshots, current owner/authority, conditional future price, separate release/human gates. Снимки четырёх исходников и документов находятся в `/tmp/graf-f280-optional-flow.md`; source review не переносится на изменённые bytes автоматически.

Окончательные UI receipts получены (`/tmp/graf-f280-optional-ui.md`, freeze2026-10-01T18:29:45+00:00); snapshot source bytes не менялся. Независимый повторный requirements review PASS51/0 текущих документов добавлен в review-optional-renewal-requirements.md, analyze актуализирован. Получены и перечитаны `/tmp/graf-f280-optional-security.md` и `/tmp/graf-f280-optional-browser.md`: оба scoped PASS0 findings и одинаковые source hashes. Независимый browser reviewer также просмотрел шесть текущих снимков Chromium/WebKit; security reviewer самостоятельно оценил renewal planner и authority fences. Вместе с flow обзором выполнены три независимых заключения T021. Больше локальных validation pending по T021 в отчёте нет; задачи не менялись.

Следующий обязательный этап — T022 exact-SHA PR/Full/CD/runtime/publication. T011/T012/F278 остаются открытыми отдельными критериями всей F280. Автор отчёта не выполнял commits/GitHub/release/deploy/live payments и не запускал новых тестов, задачи не менял.

Основной агент перечитал три независимых заключения и финальные receipts: source hashes совпадают, новых concrete code findings0, новые missing implementation tasks0. В tasks добавлена явная ссылка Issue7408 для каждого нового task; отметки T020/T021 обновлены после проверки, T022 открыт. Требования и объём не менялись.
