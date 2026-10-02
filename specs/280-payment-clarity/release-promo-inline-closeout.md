# F280 — выпуск проверки промокода без перезагрузки

Выпуск `v2026.10.02.7` опубликован2026-10-02T21:57:43Z и развернут на SHA `78f9a1207a4aba6ef1ecaf85431888d1e055dd95`. T026–T028 завершены. Lane: high-risk-product + release-deploy; документация закрытия — scoped docs. Изменения интерфейса, сообщения отказа и сохранение выбранного продления доставлены. Настоящая финансовая и человеческая приемка остаются отдельными.

## Исходный код и проверки

PR7465: tested head `b0109f94d2d467ca1901326514802c2ab03b3d48`, squash `c6737dacddec1879fe4fa97cc9c5aceee3a3371a`. Общий validator PASS: governance-fast37066721665, macos-pr37066721791, pr-metadata37066719252; checked base `3bb2edf47b4cd53f59a690bc12a178427f83b60d`. Два замечания review исправлены и разрешены по RED/GREEN и независимой повторной проверке. PR7467 подготовки: head `e6462d4a1f6c115a9f2802811b47270e5bce845b`, common validator PASS; merge является SHA выпуска.

Локальные proof: Chromium28/WebKit28, HTTP/domain205, account6, money237, recovery30, accessibility16+16 и static76 PASS. После последнего template-only исправления UI74/account6 и Chromium2/WebKit2 PASS на320/1280: явное восстановление year без draft сохраняет период/сумму/False, новая оферта unchecked,0money POST. Границы неизменного JS/серверных файлов и более ранних полных наборов честно отражены в validation-promo-inline.md и validation-promo-inline-pr-followups.md. Независимые flow/security/browser reviews плюс повторный read-only template review: применимых открытых замечаний0. Requirements checklist16/0, source converge без новых задач.

Хеш clarity regression в прежнем metadata был снят до удаления исполнителем одной пустой строки перед коммитом. Только этот непроизводственный digest уточнен по фактическому файлу, прошедшему GitHub PR и frozen Full; причина и прежний digest сохранены. Производственные hashes не менялись.

## Замороженный выпуск

Train `train-20261002T213956Z-78f9a1207a4a` включает фактический диапазон после опубликованного v2026.10.02.6: PR7442,7465,7467. Candidate `rc-20261002T214044Z-2125936b6662`; единственный [release-full37068251644](https://github.com/yshishenya/graf/actions/runs/37068251644) PASS на указанном SHA, включая восемь серверных групп, strict/performance, static/governance, macOS и aggregator. Full digest `sha256:2c7f114ce7145db5c248f49544fb0c608810415a7ba581427478a16d19ca23a2`. Train/decision GO, tag и отдельная publication attestation соответствуют exact source. Старые frozen records не переписаны.

Первый execute остановился локально с branch_mismatch до remote mutation: checkout был detached при требуемой master. Историческая запись незавершенной попытки сохранена. В изолированном собственном clone master была свободна; переключение и fast-forward оставили тот же78f9a120, clean worktree. Штатные candidate/train validate --current снова PASS; release --from deploy продолжен с тем же immutable GO и одним Full. Проверки, evidence и защитные условия не отключались. Это операционный повтор после локального отказа, не изменение кандидата и не подмена CI.

CD dry-run и execute PASS. Deploy245с, этап драйвера250с; backup20261002T215332Z. readiness=infra_smoke_ready; playback/normalization остается worker_capability_only. Откат не потребовался и не выполнялся.

## Работающий сайт

Независимое чтение установленных файлов после rollout: rec-api, rec-processing-worker, rec-maintenance имеют SHA выпуска и36/36 совпавших digests двенадцати billing файлов. Службы running; публичная оплата включена, scope public, production/ожидаемый магазин и provider observation сохранены. API и processing healthy; maintenance без отдельного health статуса.

Публичные live/ready/download/checkout HTTP200. Checkout без входа ведет на вход. Публичный cabinet.js SHA256 `95f5d619f7cab0d70e1b604f0c6fccaba5ce47b91c756ae4fc9073ac75baeb34`, установленный template `9c68661848504e02b02f067f7e2a3f759fa0c04fd7f808354e4388c1d06d54b2`. Пакет9259700байт, SHA256 `b5df859986d0ad36a07302c87c598b7a7d6e027a65e4024dd70fe0cba3338662`: прежние подписанные байты сохранены, macOS не пересобирался. Авторизованное прохождение настоящего кода в production этим public GET/source proof не заявлено.

## Границы закрытия

Закрывается только #7460 после подробного русского комментария и live issue-closeout validator. T011/T012, F278/#7285 и umbrella#7366 остаются открытыми: реальные деньги/карта/повторное списание/чек/банк/возврат, установленный Dev, приемка людьми и конверсия/удержание не доказаны. Письмо ЮKassa о подключении и продление прежнего промокода подтверждены отдельно в существующих отчетах; повторных денежных запросов за пользователя не было.

[Метаданные выпуска](evidence/promo-inline-release.json). Документы создаются после публикации и не изменяют frozen исходный код. Исторические RED/PENDING сохранены как записи своего этапа.

Независимая заключительная read-only проверка: PASS, применимых замечаний0. Рецензент отдельно сравнил36/36 runtime и10/10 source digests с git show коммита выпуска, проверил Full/decision/publication и границы приемки. [Отчет](review-promo-inline-release.md).
