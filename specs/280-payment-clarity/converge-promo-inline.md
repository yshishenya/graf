# F280 — сходимость проверки промокода без перезагрузки

Дата:2026-10-02. Lane: active Spec Kit slice / high-risk-product. Оценка относится к FR024–030/SC010–012 и T026–T028 существующей F280. Поддерживаемый `check-prerequisites.sh --json --require-tasks --include-tasks` подтверждает активную фичу; spec прочитан явно. Hooks before/after_converge отсутствуют.

| Источник | Реализация и доказательство | Состояние |
| --- | --- | --- |
| FR024 | Понятные отдельные promo/account сообщения; typed budget error после rollback; все действующие callers | Domain29 и HTTP205/account6 PASS |
| FR025 | Existing HTMX form/target/select/outerHTML, Apply/Enter/remove/cycle; native start/fallback | Source соответствует, full browser28+28 PASS |
| FR026 | Bool preference в памяти/optional storage с полным user/workspace/session scope; False после ошибок; offer unchecked | Scoped Chromium/WebKit storage PASS; rail fix |
| FR027 | Single request/busy/start block/manual recovery/15s native timeout; scope/current target checks/direct once xhr.loadend | Boundary5 Chromium4/WebKit4 PASS, независимый retry1 PASS |
| FR028 | Existing server quote/owner/CSRF/receipt/idempotency/provider/financial invariants без новых переходов | Money237/recovery30 PASS |
| FR029 | Safe cycle replaceState; draft300с и quote10мин остаются разными; code не добавлен в историю | Source и boundary proofs; full browser28+28 PASS |
| FR030 | Status/alert/aria-busy/keyboard focus/details/recovery и native forms | A11y Chromium16/WebKit16 PASS до узкого loadend fix; full browser28+28 PASS |
| SC010 | Реальные browser→HTTP→SQL sequences; window/document/history, True/False/storage/fallback | Итоговая full матрица28+28 PASS |
| SC011 | Timeout/network/status/scope/late/detached/fresh retry без старого start/quote и финансовых действий | Boundary PASS; итоговая full матрица28+28 PASS |
| SC012 | Не смешаны promo/account/provider причины; независимые current code reviews, честные границы | Flow/browser статический PASS; security PASS; final runtime pending |
| T028 | GitHub current SHA/base, frozen Full, CD/runtime/publication/closeout | Существующая задача доставки; не дублируется |
| T011/T012/F278 | Реальные платежи/карта/чеки/банк/возвраты и человеческая приемка/конверсия | Сохраняются открытыми |

Проверены10 новых требований/критериев,6 нумерованных решений плана: existing preview/HTMX; ordinary start/noJS; scoped optional bool; complete response authorization; safe public typed refusal; separate server release. Применимы5 принципов constitution II/III/V/VI/VII (управление, минимизация/безопасные доказательства, публичная подпись, Spec Kit gates, доступность/свои ресурсы); I/IV неизменны вне области среза.

Новых source findings missing/partial/contradicts/unrequested0, CRITICAL/HIGH/MEDIUM/LOW0 после устранения M1, H1 и M2. Новых обязательных исполнительных задач не требуется; все оставшиеся проверки и выпуск уже находятся в T028. Invocation converge не переписывает tasks и не добавляет пустой phase. Это source-converged с завершенными локальными проверками и незавершенными воротами выпуска, не полное закрытие F280 или финансовой приемки.

Текущий JS SHA256 `95f5d619f7cab0d70e1b604f0c6fccaba5ce47b91c756ae4fc9073ac75baeb34`. Окончательные факты дополняются из validation-promo-inline.md, review-promo-inline-final.md и release-promo-inline-closeout.md только после завершения соответствующих проверок.


Повторная сверка после двух замечаний PR7465: account_unavailable убирает денежные действия без ложного pending, recovery href сохраняет только проверенный cycle. FR024/025/027–029 и SC010/012 уточнений intent не требуют; пять RED contract и browser RED сменились UI74/account6/Chromium2/WebKit2 GREEN. Независимая повторная проверка template PASS, clarity21PASS. Проверенные количества требований/решений/принципов прежние; новых обязательных задач0. Все оставшиеся gates относятся к действующей T028. Converge не изменяет tasks.
