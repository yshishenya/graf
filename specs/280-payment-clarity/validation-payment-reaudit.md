# F280 — проверка исправлений повторного аудита

Дата: 2026-10-16. Полоса high-risk-product существующей F280, затем release-deploy. Исходная база 0a235f175bed306324064b68a7c1e38bffa322b0; текущие изменения еще не выпущены. Действующее разрешение владельца включает проверенный коммит, PR, обычное слияние и production. Денежные операции и отправка писем этим проходом не выполняются.

## Причинная проверка

На прежнем billing.py один изолированный HTTP/PostgreSQL набор получил 50 failed / 21 passed / 0 skipped: 40 отказов трех start recovery веток, 5 ложных утверждений об оплате из query и 5 неподходящих GET continuation. Финансовые snapshots и запрет create проверяются теми же тестами. Отдельный прежний HTML четырех copy callers дал 4 failed / 16 deselected: unbound buttons не были скрыты. Отказы сохранены в локальных диагностических журналах; сырые журналы и локальные пути в репозиторий не включены.

## Изменения

- Один predicate проверяет текущее пространство, связанный pending invoice, provider_pending operation, подходящий вид, плательщика, provider_id для initial и разрешенный URL. Все три start recovery ветки читают tenant-scoped invoice до решения; GET checkout/status и hosted continue используют тот же predicate. Локальный статус/fallback сохраняется. Новые invoice locks не добавлены.
- Legacy explicit no-provider dispatch сохраняет отдельные прежние условия и ключ; expiry/blocking policy не меняется.
- Receipt error paid wording требует succeeded invoice. Receipt-only права, service_gap и доступ к документам не изменены.
- Четыре copy buttons скрыты до binding; fallback возвращает клавиатурный фокус. Источник текста и прежнее честное live сообщение доступны.

## Проверки

Первый PR HEAD `44878280d9dda08b792cd75cb6bc611b992465a4`: macos-pr и pr-metadata PASS; governance-fast [38808737767](https://github.com/yshishenya/graf/actions/runs/38808737767) FAILED, 6 failed / 174 passed. Все шесть отказов относятся к `test_confirmed_payment_grants_access_and_survives_replays` (`renew`, `once`, `omitted` × `month`, `year`): после доказанных invoice/operation succeeded прежний тест требовал вернуть старый hosted URL. Это противоречит FR053. Причинный локальный повтор неизмененного теста воспроизвел 6 failed / 0 skipped за13.66с. Изменено только итоговое ожидаемое Location на локальный статус того же счета; pending replay продолжает требовать прежний hosted URL. Проверки сумм, доступа, сроков, сохраненных согласий, provider calls, повторов webhook и количества grants сохранены. Product код не изменен. Новый полный money-path результат и exact-SHA GitHub gates обязательны до слияния.

| Проверка | Наблюдаемый результат |
|---|---|
| Полные test_billing_clarity.py и test_billing_ui.py, изолированный PostgreSQL | 289 passed, 0 skipped, 142.30с; disposable container штатно удален |
| Initial checkout recovery + billing security | 28 passed, 1.56с |
| Cabinet static assets + settings contract/view models | 112 passed, 3.58с |
| Presentation billing_clarity contract | 21 passed, 0.21с |
| Spec Kit governance, fragment schema, Ruff измененных Python, JS syntax, whitespace | PASS |
| Полные sibling return/purchase/promo | 250 passed, 0 skipped, 391.72с; дополнительный набор с17unit recovery —267 passed, 396.85с. Оба контейнера штатно удалены |
| Полный money-path после исправления terminal replay ожидания | 71 passed, 0 skipped, 48.80с; runner exit0, disposable PostgreSQL штатно удален; все денежные assertions сохранены |
| Browser Chromium/WebKit | PASS: Chromium59 в66.51с (accessibility+support), WebKit20 в90.35с; полные матрицы, без skipped |
| Независимый requirements gate | 127 checked / 0 unchecked; report сохранен отдельно |
| Независимый final source/browser обзор | PASS, применимых новых critical/high/medium нет; product hashes сверены |
| Exact PR SHA/base gates и production | Еще не выполнены |

Зависимости не добавлены, API/БД/миграции/цены/вычисления/согласия и геометрия не изменены. CI plan подтверждает partial local coverage и обязательные GitHub gates, затем один frozen release-full. Два предупреждения Python относятся к существующим pytest import/httpx deprecation, тесты не пропущены.

Первые браузерные прогоны остановились на300с. Причина: новый JS-off helper пытался выполнить page.addStyleTag при выключенном JavaScript. CSS включен в исходный synthetic HTML; product не менялся, лимит300с, существующая матрица и assertions сохранены. Повторные полные результаты выше подтверждены завершенными журналами.

## Границы

Технические проверки не закрывают T011 установленного GRAF Dev, T012/SC005/006 с участниками и метриками, F278 банк/возврат/реальное продление или подтверждение доставки почты. Эти критерии остаются отдельными. Чужая параллельная storage/mail работа и перенумерация не включены в код этого среза. Общий оператор владеет единственным выпуском; исторические версии и CI не являются доказательством новых байтов.

Свежий read-only `dev-harness.sh status --json`: status=active, установлен единственный GRAF Dev, manifest dev-47ea28967f9c / F286, source47ea28967f9cca89f793b50cef8371ee36f3a381. Стенд не обновлялся и приложение не запускалось этим срезом; эта версия не подтверждает установленную приемку новых исправлений F280.

## Подтверждение слияния 2026-10-16

PR [#7606](https://github.com/yshishenya/graf/pull/7606) объединен штатным squash 15 октября в21:48:27UTC. Проверенный head `698ebfa5202986f1a681fd46eb4f12e505352ded`, base `d567a7dc51b0c4d99b22660d27950316ae609a66`, merge `e8d85cabc1246e1774b0af0b385d8e3a61fda237`. Общий `scripts/validate-pr-checks.py` подтвердил точные обязательные доказательства: [governance-fast](https://github.com/yshishenya/graf/actions/runs/38810862734), [macos-pr](https://github.com/yshishenya/graf/actions/runs/38810862776), [pr-metadata](https://github.com/yshishenya/graf/actions/runs/38810897599). После исправления единственного устаревшего terminal replay ожидания полный money-path71PASS/0skipped, независимый обзор PASS; продуктовый guard не ослаблялся. T062 отмечена выполненной на этих доказательствах; T065 остается открытой до общего выпуска.

Владелец исправлений затем выполнил штатные build/promote/smoke единственного GRAF Dev с тем же head, manifest `dev-698ebfa52029`, feature280. Подпись и разрешения сохранены; smoke и exact_source_sha PASS. Наблюдались переходы Настройки → Тариф и оплата → Хранилище → помощь → история, Tab/Return и Назад/Вперед. Это частичная T011: в локальной конфигурации checkout отключен, нет счетов и не настроена поддержка. Оплаченный документ, переход к провайдеру и возврат, полная проверка тем и масштаба не подтверждены; T011 остается открытой. Платежи, письма и запись для этой проверки не выполнялись.


## Серверный выпуск 2026.10.16.1 — 2026-10-16

Источник `79804a512a50e94e618ff3380b472d7f027963d6` выпущен штатным CD и опубликован как [v2026.10.16.1](https://github.com/yshishenya/graf/releases/tag/v2026.10.16.1). Единственный успешный Full исправленного кандидата [38816153046](https://github.com/yshishenya/graf/actions/runs/38816153046), GO/dry-run/execute PASS, runtime10/10 и application source labels совпали;175 публичных файлов сохранены, три скачанных файла совпали. Подробные доказательства, первая остановка на написании F282 и границы — в [deployment](../../docs/deployments/2brain-rec/release-v2026.10.16.1.md).

**T065 пока открыта:** действующего пользовательского сеанса для финальных safe GET нет, текущий браузер показывает auth_session_invalid; причина этим не установлена. Запрошен штатный вход без новой оплаты, писем от агента или обхода auth. После входа нужны подписка/история/существующий оплаченный документ/копирование. T011/T012/F278 не закрываются; частичная установленная приемка GRAF Dev не заменяет оставшиеся сценарии. Отметки checklist root не менял.
