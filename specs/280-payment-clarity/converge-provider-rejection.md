# F280 — сходимость отказа начала оплаты

Дата: 2026-10-02. Lane: active Spec Kit slice / high-risk-product. Ветка `codex/280-payment-provider-rejection`; активный указатель и supported `check-prerequisites.sh --json --require-tasks --include-tasks` подтверждают F280. Файл spec прочитан явно: upstream `--require-spec` не поддерживается установленным скриптом. Hooks before/after_converge отсутствуют.

| Источник | Реализация и доказательство | Состояние |
| --- | --- | --- |
| FR-021 | Stored schema2/canceled invoice+operation/no provider/safe typed HTTP → новый заголовок; generic403 без выдуманной причины, bound cancellation прежняя | Source соответствует; adapter/HTTP matrix |
| FR-022 | Fixed recurring403 +initial+savedTrue; existing retryyear; defaultTrue/offerunchecked; manualFalse/explicitPOST | Chromium8/WebKit8, обе ширины; HTTP retry |
| FR-023 | Allowlist reason constructor +snapshot; raw response/id не сохраняются; query не авторизует причину; unknown/manual без новой оплаты | Security PASS, adapter/recovery45, UI/HTTP отрицания |
| SC-009 | Один rejected dispatch, неизменный старый snapshot, repeatedGET/duplicatePOST, releasedpromo/budget, новая явнаяFalse/quote/offer | Настоящий DOM→HTTP→SQL, unit/HTTP batch |
| FR-003/007/010/011/012/015/018/020 | Цена, period, явный режим, offer/owner/CSRF/receipt/idempotency, existing promo lifetime и consumed draft, keyboard/noJS граница | Прежние браузерные/HTTP/security регрессии сохранены |
| T025 | Exact-SHA PR, новый frozenFull, dry-run/execute/runtime/publication | Уже существующая задача выпуска; не дублируется |
| T011/T012/F278 | Dev/human/conversion/реальные деньги/банк | Отдельные открытые критерии, синтетической проверкой не заменяются |

Проверены3 новых FR,1SC,8 связанных инвариантов;6 решений плана: existing adapter/routes/template, fixedreason/no raw, snapshot authority, defaultTrue/manualFalse, unknown protection, отдельный server-only выпуск. Нормативные ограничения конституции применены: явное управление, минимизация данных, Spec Kit/reviewer gates, доступность/собственные ресурсы, честные границы приёмки.

Новых source findings missing/partial/contradicts/unrequested0, CRITICAL/HIGH/MEDIUM/LOW0. Изменённых финансовых переходов или новых механизмов оплаты нет. T025 уже покрывает оставшиеся release gates; T011/T012/F278 сохраняют исходный объём. Новых исполнительных задач не требуется, convergence не переписывает tasks и не добавляет пустой phase. Это source-converged, не полное закрытие F280 или подключение автоплатежей. Локальная приёмка определяется завершённым [validation-provider-rejection.md](validation-provider-rejection.md); три independent PASS с hash snapshot — [review-provider-rejection-final.md](review-provider-rejection-final.md).
