# F280 T061 — проверка раскрытия помощи

Полоса: active Spec Kit slice, узкая test-only поправка; выпуск отдельно release-deploy. Issue7537.

## Причина и минимальное исправление

Frozen rc-20261004T045654Z-403d757ab492 на11d2b2d35e9c7f0f723ec92f79ad0d572b0c9778, release-full [37178472845](https://github.com/yshishenya/graf/actions/runs/37178472845) FAILURE: shard1 —1failed/820passed/10skipped. Остальные7shards, server static/strict-performance и macOS PASS; aggregate отказал до authoritative artifact. Ни GO, ни CD не было. Frozen record сохранен; отдельный abandonment record фиксирует неуспешный неопубликованный выпуск.

Старое html.replace billing-coupon имеет0совпадений в invoice; пояснения безусловно присутствуют внутри закрытого settings-disclosure. Только selector в existing contract test заменен на точный details+summary «Помощь и возврат»; соседние сведения остаются закрытыми. Parser/context/decorators/assertions unchanged. Ни product, ни помощь parser, ни денежные/query/API/DB/flags/consents/CSRF не менялись.

## Причинные и полные проверки

В apps/server: `uv run --extra dev pytest tests/contract/test_billing_clarity.py -k invoice_refund_disclosure -q --tb=short --show-capture=no`: RED1failed/20deselected0.12s → GREEN1passed/20deselected0.07s. Полный touchedfile той же командой без-k:21passed0.09s. Ruff/diffcheck PASS. Все прежние закрытые и раскрытые финансовые пояснения/link/noform assertions сохранены; AST независимый обзор подтвердил неизменность5assert nodes.

Независимые [требования](review-invoice-t061-requirements.md): checklist16checked0unchecked,0/0/0. [Исходники](review-invoice-t061-source.md):0critical/0high/исправимыхmedium0. Target совпадает1раз, только help раскрыт. Предыдущие17source/test hashesMATCH; новый contractSHA2568314a40b2b40f19ca2ffac278c359add1d5206d4a999d2c3ac4a4de7ca423d92, общий18manifestMATCH root после переноса. Локальные ephemeral логи и receipts сохранены оператором, приватные сведения не включены.

## Сверка реализации и выпуск

Scoped converge: существующие FR049/052/SC017 и CHK006/010 покрыты; других реализуемых пробелов не выявлено. T061 оставлена открытой до собственных точных PR gates/merge и общего выпуска T048/T056. Подготовка .04.5 повторно прошла штатным prepare-release после abandonment, опубликованная .04.4 сохранена. Будущие CI/Full/GO/CD/publication/live не объявляются успешными. Финансовая/человеческая/installed приемка и F278 остаются отдельными. Legacy Impact untouched.

## Актуальное подтверждение выпуска 2026-10-04

Исторические ожидания CI/выпуска выше сохранены по времени наблюдения. Текущий серверный source `e50c4a729cdb2cd4d1d9a59c27637410bcd8b908`: обычные PR7506/7532/7536/7538 и обязательные exactSHA/base checks PASS; source18/18 MATCH; authoritative [Full37180461213](https://github.com/yshishenya/graf/actions/runs/37180461213) SUCCESS, новый frozen candidate/GO, штатный CD dry-run/execute PASS, runtime12/12 product files и три service SHA MATCH, флаги публичной оплаты/наблюдения/всех пространств true. Обе живые страницы проверены только GET, public artifacts3/3 unchanged, stable tag/Release v2026.10.04.5 и publication attestation на том же источнике подтверждены. [Итог выпуска](release-subscription-clarity-closeout.md) и [подробный отчет](../../docs/deployments/2brain-rec/release-v2026.10.04.5.md) содержат независимые обзоры и пределы. Предыдущие failed кандидаты и неустановленная причина macOS timing failure не удалены; диагностический PASS не подменяет authoritative Full. Финансовая, человеческая, установленная приемка и SC005/006/F278 остаются открытыми. Новых реализуемых пробелов этого среза нет.
