# F280 — независимый аудит общего выпуска подписки и платежного документа

Reviewer: `subscription_browser_final`, независимый от реализации и операции
выпуска. Lane: read-only audit требований и доказательств выпуска. Ownership:
только этот отчет; код, требования, задачи, reviewer checklists, Git/GitHub,
release/deploy не изменяются. Новые тесты, браузер, приложение и платежи не
запускаются.

## Снимок до заморозки — 2026-10-04, 01:02 UTC

**HOLD: выпуск пока не доказан и не разрешен этим аудитом.** Новых
обязательных исправлений T057 из прочитанных доказательств не выявлено;
готовность общего выпуска зависит от открытых ворот ниже.

Canonical source: T048/T056/T057 в `tasks.md`, действующий
`quickstart.md`, `converge-subscription-clarity.md`, отчеты требований/source/
UX/browser T057 и `validation-subscription-t057.md`,
`docs/agent-guidance/release-and-validation.md`, `.github/pr-check-policy.json`.
Разрешение владельца на технические commit/merge/production действия уже дано;
повторный запрос разрешения не является воротом этого выпуска. Настоящие
платежи/списания/возвраты/grants в проверку не входят.

### Подтверждено чтением, без нового запуска проверок

- Текущий чистый исходник подписки:
  `ebbd27d9d44fd50bca3b9f1817d838aee5592a42`, PR
  <https://github.com/yshishenya/graf/pull/7506>. В отчете source отмечено
  однострочное нейтральное сообщение, сохранение prepared исключения,
  денежных handlers/query/guards и исправление прежнего literal ожидания
  без удаления финансовых assertions.
- Requirements14/0 и три отдельных source/UX/browser заключения T057
  сообщают 0critical/0high/0исправимыхmedium. Это отдельные виды доказательств,
  ни одно не заменяет GitHub gates или production.
- Самостоятельно пересчитаны SHA256 восьми текущих файлов и сверены с
  `validation-subscription-t057.md`: **8 совпадений, 0 отличий**. Следовательно,
  сохраненные узкие заключения относятся к нынешним байтам T057 после
  коммита, несмотря на исторический parent HEAD в самих отчетах.
- Самостоятельно прочитаны окончания сохраненных журналов: PostgreSQL
  **240 passed, 181.26с**, focused runner PASS/isolated cleanup; Chromium
  **16 passed, 42.19с**; WebKit **16 passed, 47.73с**. Это чужие завершенные
  focused/synthetic прогоны, не самостоятельный повтор и не `release-full`.
- Через GitHub API подтвержден актуальный опубликованный stable Release
  `v2026.10.04.2`, `published_at=2026-10-04T00:08:55Z`. Annotated tag object
  `63d8f9849ff7f63a44856f7c25c9c7c05d419753` разрешается в commit
  `0d4283e02a657beba8a971e7c6023cc69fef39ba`. Эта опубликованная база заменяет
  старые снимки о draft `.04.1/.04.2`. Ее актуальность и свободный номер
  нового CalVer оператор повторно сверяет непосредственно перед подготовкой.

### Открытые ворота

| Ворота | Состояние снимка | Нужное окончательное доказательство |
| --- | --- | --- |
| Exact SHA/base PR7506 | OPEN; head `ebbd27d9…`, base `0d4283e0…`, `mergeable_state=behind`, `merged=false`; governance/native выполняются, latest metadata SUCCESS | Текущий common `validate-pr-checks.py` PASS всех трех обязательных contexts с реальными source proofs/checked base; нормальное слияние и merge SHA |
| Invoice peer T052–T055 | OPEN; переданная краткая идентичность `db2baf` не разрешается в этой копии; canonical задачи пока открыты | Полный PR/head/base, текущие требования/валидация/независимые обзоры/converge, common validator PASS, merge SHA; подтверждение, что согласованные оба среза в общем источнике |
| Release metadata | OPEN | Новый незанятый CalVer, подготовленный русский changelog/owned fragments, штатный reviewed release-prep и clean source SHA |
| Immutable train/candidate | OPEN | Manifest реального диапазона после последней опубликованной stable базы, все включенные PR/Feature IDs, синтетическая provenance и post-merge source SHA/changelog digest; current validate/freeze PASS |
| Authoritative Full CI | OPEN | Ровно один current `release-full` для candidate ID, полный server+macOS, source/component SHAs и digests; artifact по canonical authoritative пути, без failed/skipped/stale proof |
| Решение выпуска | OPEN | `train-attest`/`decide` GO на том же candidate/source/changelog/evidence digest; изменившиеся байты требуют нового candidate |
| Production | OPEN | Штатный CD dry-run, затем execute с GO/evidence; fresh backup, актуальная restore readiness, migrations/RLS/secret/health/smoke и повторная Temporal/worker readiness |
| Live feature evidence | OPEN | Runtime image/source соответствует одобренному SHA; публичный health/download и разрешенное чтение защищенных обновленных subscription/invoice/status поверхностей, без новых денег |
| Public publication | OPEN | Annotated CalVer tag на одобренном SHA, русский non-draft stable GitHub Release, immutable publication attestation |
| Rollback/closeout | OPEN | Честный rollback status и deployment report; `not_required` не доказывает живой откат. Evidence-backed закрытие только действительно принятых задач/связанных issues |

API snapshot PR7506 содержит несколько contemporaneous runs, включая старый
отмененный metadata и еще выполняющиеся source/text gates. Одного успешного
metadata, scope job или старого source PASS недостаточно. Только общий
validator выбирает допустимую текущую цепочку head/base/run/attempt и повторно
проверяет ее. `mergeable_state=behind` требует актуальной проверки политики
свежести перед нормальным merge, не обхода через admin.

## Проверенные границы выпуска

T048 и T056 требуют **один общий серверный выпуск после готовности и merge
обоих согласованных срезов**. Имена candidate/version пока не выбраны данным
reviewer. Прежний candidate/draft не присваивается новому источнику; подготовленный
changelog без опубликованного Release не становится stable базой. Collector
должен учитывать весь фактический диапазон PR после опубликованного tag.

`release-full` запускается после release metadata на frozen source и содержит
server+macOS. Focused240/82/16+16, прежние PR CI и diagnostic receipts не
заменяют это доказательство. Одна authoritative identity используется повторно
при CD, без второго полного прогона для того же candidate. Изменение source
или changelog после freeze делает старое решение неприменимым.

Публичный macOS пакет не перевыпускается только ради этой серверной страницы.
Штатный CD сохраняет существующие регулярные непустые runtime `graf.pkg` и
проверяет их доступные байты; новые macOS artifacts, если их scope неожиданно
возникнет, потребуют отдельного Developer ID/notarization/stapling/Gatekeeper/
Sparkle доказательства. Занятый GRAF Dev не запускается и его ручная приемка
не приписывается synthetic web проверкам.

Русские Release notes должны описывать изменения, проверки, совместимость/
миграции, ссылки на PR/issues, эксплуатационные ограничения и rollback.
Evidence содержит только metadata; без пользовательских screenshot, платежных
идентификаторов, контактов, карт, секретов, private paths или raw content.

T011/T012, SC-005/006, финансовая приемка F278 и umbrella #7366 этим выпуском
не закрываются. Рост конверсии, желание каждого пользователя платить, реальное
банковское зачисление, чек, возврат и будущие автосписания не следуют из
локальной готовности или самого технического production выпуска.

## Ожидание окончательного аудита

Оператор передаст конкретные merged source/PR proof, train/candidate ID,
authoritative CI, GO, CD, runtime/live/publication и rollback данные. До
самостоятельного чтения и сверки их связей этот отчет остается **HOLD**.
Применимые source/PR/release изменения после этого снимка проверяются на новых
байтах; исторические доказательства не переносятся автоматически.
