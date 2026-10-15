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

| Проверка | Наблюдаемый результат |
|---|---|
| Полные test_billing_clarity.py и test_billing_ui.py, изолированный PostgreSQL | 289 passed, 0 skipped, 142.30с; disposable container штатно удален |
| Initial checkout recovery + billing security | 28 passed, 1.56с |
| Cabinet static assets + settings contract/view models | 112 passed, 3.58с |
| Presentation billing_clarity contract | 21 passed, 0.21с |
| Spec Kit governance, fragment schema, Ruff измененных Python, JS syntax, whitespace | PASS |
| Полные sibling return/purchase/promo | 250 passed, 0 skipped, 391.72с; дополнительный набор с17unit recovery —267 passed, 396.85с. Оба контейнера штатно удалены |
| Browser Chromium/WebKit | PASS: Chromium59 в66.51с (accessibility+support), WebKit20 в90.35с; полные матрицы, без skipped |
| Независимый requirements gate | 127 checked / 0 unchecked; report сохранен отдельно |
| Независимый final source/browser обзор | PASS, применимых новых critical/high/medium нет; product hashes сверены |
| Exact PR SHA/base gates и production | Еще не выполнены |

Зависимости не добавлены, API/БД/миграции/цены/вычисления/согласия и геометрия не изменены. CI plan подтверждает partial local coverage и обязательные GitHub gates, затем один frozen release-full. Два предупреждения Python относятся к существующим pytest import/httpx deprecation, тесты не пропущены.

Первые браузерные прогоны остановились на300с. Причина: новый JS-off helper пытался выполнить page.addStyleTag при выключенном JavaScript. CSS включен в исходный synthetic HTML; product не менялся, лимит300с, существующая матрица и assertions сохранены. Повторные полные результаты выше подтверждены завершенными журналами.

## Границы

Технические проверки не закрывают T011 установленного GRAF Dev, T012/SC005/006 с участниками и метриками, F278 банк/возврат/реальное продление или подтверждение доставки почты. Эти критерии остаются отдельными. Чужая параллельная storage/mail работа и перенумерация не включены в код этого среза. Общий оператор владеет единственным выпуском; исторические версии и CI не являются доказательством новых байтов.

Свежий read-only `dev-harness.sh status --json`: status=active, установлен единственный GRAF Dev, manifest dev-47ea28967f9c / F286, source47ea28967f9cca89f793b50cef8371ee36f3a381. Стенд не обновлялся и приложение не запускалось этим срезом; эта версия не подтверждает установленную приемку новых исправлений F280.
