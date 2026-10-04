# F280 — независимый окончательный обзор технического выпуска

## Итоговый аудит v2026.10.04.5

2026-10-04, после publication attestation06:01:58UTC. Reviewer `/root/subscription_browser_final`, независимо от реализации и операции выпуска. Полоса `release/deploy`, исходная работа F280 — `high-risk-product`. Ownership только этот временный отчет. Product suites, частный браузерный кабинет, GRAF Dev, платежи, письма, Git/GitHub и deploy reviewer не изменял и не запускал. Выполнены read-only чтение доказательств, GitHub API, локальное вычисление отпечатков и независимое чтение публичных файлов/health. Другие участники и их изменения сохранены.

**TECHNICAL RELEASE PASS: обязательные технические ворота выпуска текущих страниц подписки, платежного документа и связанной помощи доказаны. Открытых CRITICAL/HIGH/исправимых MEDIUM технических замечаний выпуска — 0/0/0.** Это самостоятельный окончательный вывод, а не повтор предварительного HOLD. T048/T055/T056/T061 и issues не объявляются закрытыми: административная сверка/документирование выполняется оператором отдельно. Финансовая/человеческая приемка и конверсия остаются открытыми в своей области.

### Одна непротиворечивая identity

| Связь | Проверенное значение |
|---|---|
| Release | `v2026.10.04.5`, опубликован06:00:39UTC, non-draft/non-prerelease |
| Clean source HEAD | `e50c4a729cdb2cd4d1d9a59c27637410bcd8b908` |
| Stable base | `.04.4` → `50e96292d96e36993436524c85829153feb27027` |
| Train | `train-20261004T051702Z-e50c4a729cdb`; включены7535/7532/7536/7538, фактический linear Git range совпал |
| Candidate | `rc-20261004T053741Z-1af7d009d698`, frozen05:37:41UTC |
| Authoritative Full | `github-full-37180461213`, full/passed, skipped_gates=[], все component/start/end/requested SHA равны source |
| Full evidence digest | `sha256:a5415006f6382f34875c1701637ccb9c7bee76cf22fa9e78ceb91ae16201835f` |
| Changelog digest | `sha256:17f61452481f741337d44c8a184fc7efef383795831195cc5577dcaab5c9a505` |
| GO | current immutable decision + train-go связаны с тем же candidate/source/Full/changelog |
| Runtime | rec-api / rec-processing-worker / rec-maintenance — тот же полный source SHA |
| Annotated tag | object `213e4ac66d21d7eb2ef3f104ad11fb63005a6abc` → exact source commit |
| Publication | `pa-rc-20261004T053741Z-1af7d009d698`,06:01:58UTC; source/tag/release target и decision digest совпали |

Самостоятельно пересчитаны18manifest файлов frozen source: **18/18MATCH, дрейф0**, чистое рабочее дерево. T061 requirements/source report отпечатки также совпали с merged-source acceptance. Чтение candidate/decision/train-go подтвердило current source и реальный диапазон после последнего опубликованного stable. Самостоятельное вычисление canonical authoritative JSON digest и CHANGELOG digest совпало с GO; publication decision digest совпал с фактическим decision file.

### Exact PR/base и полное доказательство

Лично прочитаны common validator receipts и независимо сопоставлены с текущим GitHub API. Все четыре PR merged, реальные checked base/head/merge связаны линейно:

| PR | Final checked head | Base → merge | Три required run ID |
|---|---|---|---|
|7535/docs | `25fb7470e81a451ea3b9c18cedbfdff6c398a3c6` | `50e96292…` → `872d5b2d…` |37174915946 /37174915938 /37174916039 |
|7532/invoice,T060 | `deb639ca8613daebfc31473ecc9418cdcaa1362f` | `872d5b2d…` → `498c9a29…` |37176667299 /37176667451 /37176666833 |
|7536/prep | `ad54ee020824a875aa5fe25aa7531b8d5ddb624b` | `498c9a29…` → `11d2b2d3…` |37177918864 /37177918866 /37177940583 |
|7538/T061 | `9fd83a7cc597e1f0421170a8b3a31cc0ae88f7b4` | `11d2b2d3…` → `e50c4a72…` |37179198078 /37179198054 /37179197339 |

Все12указанных run через текущий API completed/success, attempt1, exact checkedhead совпал. Receipts содержат source proof digests и metadata digest; prep/T061 receipt записан до merge, его merge=null не выдавался за состоявшееся слияние — фактический merge самостоятельно разрешен API/Git. Текстовое EOF исправление report сохраняется исторически; failed d184 проверки не используются как допуск finaldeb639.

Текущий Full37180461213 самостоятельно прочитан через API: completed/success/attempt1 на exacte50c. Все13работ успешны, включая macOS Swift full, Ubuntu strict/performance/static, восемь parallelshards и aggregateauthoritativeFull. Результаты сохраняются в единственном canonical `.dev/ci-evidence/authoritative-rc-20261004T053741Z-1af7d009d698.json`; другой diagnostic/failed результат на этот путь не переименовывался. Обязательное доказательство CD использовало повторно, без нового полного прогона во время execute.

Предыдущие отказы сохранены и лично сверены через API:

- Full37178472845 на11d2 остается failure: stale test имитировал раскрытие отсутствующим selector. T061 causalRED1→GREEN1/full21, requirements16/0 и independentsource0/0/0; AST сохранил прежние assertions и parser, product bytes не менялись.
- Full37179496922 наe50c остается failure по native timeout. Причина **UNESTABLISHED**, не переименована в установленную flakiness или успешную приемку.
- Diagnostic37180047879 success наe50c — отдельная диагностическая информация, не authoritative approval.

Только новый completed authoritativeFull37180461213 на новом candidate дал GO. T061 не меняет native/API workflow, product code, thresholds или assertions; исправление test selector и существующие T060 browser budget подробно ограничены в независимых отчетах. Старые failed records не изменялись и не считаются PASS.

### Deploy, runtime, откат и публичные файлы

Лично прочитан CD dry-run: candidate=go, candidate_gates=passed, local_ci=authoritative_full_reused. Execute содержит тот же source/candidate/evidence; terminal deploy_result=pass, deployed/runtimeSHA exacte50c, deploy_total243секунды. Backup pass с новым metadata reference `20261004T055148Z`; secret/DB identity/migration/RLS/image-capability/profile/media-worker/dispatch gates проходят. Smoke pass, очищены34syntheticdatabase records и3objects, residueempty. Temporal/processing readiness повторно проходит после smoke, а не только до него. Compose предупреждает о неподдерживаемых secret uid/gid/mode, но самостоятельные runtime secret permission/identity gates PASS; эти warnings не переопределяют факт успешного deploy и не скрыты.

Из прочитанного exactCDsource: `deploy_result=pass` возможен только после persisted image `finish deployed`, finalreadiness и отключения rollbacktrap с deployment_complete=1. Поэтому текущая попытка завершена deployed; rollback **not_required**, реального отката в этом выпуске не было. Train задает fallback`.04.4`; backup сохранен. Полную свежую restore rehearsal reviewer не приписывает выпуску: текущий script1058–1069 явно вынес ее в отдельное расписание; каждый deploy по-прежнему обязан иметь свежую backup. Отсутствие специально запущенного restoration drill не становится новым вымышленным воротом UI выпуска.

Metadata root runtime наблюдения05:57:35UTC и distinct peer05:58:13UTC прочитаны отдельно: три службы exactsource,12deployedproductfiles MATCH. Reviewer самостоятельно сопоставил каждый из12runtimehash с18source manifest; шесть testfiles проверены в frozen source, не выдаются за runtime. Publiccheckout=true/providerobservation=true/allworkspaces=true сохранены. Privatefinancial values и secrets не включаются в этот отчет.

После deploy reviewer **самостоятельно заново прочитал по HTTPS** три публичных файла, вычисляя digest потоком без запуска/установки приложения. КаждыйHTTP200, bytecount/SHA совпал с before-ownbaseline и двумя отдельными root/peer postdeploy проверками:

| Публичный файл | Размер | SHA-256 |
|---|---|---|
|graf-appcast.xml |6824байт |`d62c4d7f0b28b6236fded564a0123510f9676038d1eb53ded77a25f90d832579` |
|GRAF-2026.10.04.4.zip |9513282байт |`5a2c236260160f5ebcd3a695943f86ec08fc4558bf2bd437e76c4a0b95090c47` |
|graf.pkg |9259700байт |`b5df859986d0ad36a07302c87c598b7a7d6e027a65e4024dd70fe0cba3338662` |

Самостоятельные повторные публичные live/ready GET далиHTTP200, statusok/statusready. Это серверный выпуск: сохранение `.04.4` macOS файлов соответствует разрешенному scope и является PASS, новая нотарификация/установка приложения здесь не требуется. GRAF Dev занят другим срезом, его установленная/ручная приемка не заявляется.

### Live интерфейс и публикация

Лично прочитано `/tmp/f280-release5-live-acceptance.json`06:00:16UTC: основной исполнитель через CUA, существующую авторизованную Zen session и GET намеренно обновил subscription, раскрыл details, перешел в историю и существующий оплаченный invoice. В subscription видны active/paiduntil/autorenew/renewallink; в invoice сумма, оплаченный период, чек, closedinitialdetails, раскрываемая help и separatequestion/refundlinks. Итог снова subscription; money_mutationfalse/private_values_retainedfalse. Это фактическая операционная приемка root, **не собственное наблюдение reviewer частного кабинета**. Reviewer принял ее совместно с exact12runtimefiles и ранее независимо принятыми synthetic/browser/actualGET данными; не требовал повторной privateсессии или денег.

Существующие T060/T061 source/visual/requirements conclusions сохраняют0/0/0 и честные границы accessibility16×2, controls202/actualGET22, status56×2. Эти наборы пересекаются и не суммируются как отдельные уникальные тесты. FinalFull дополнительно проверил общий source. Отсутствия повторного UI теста после test-onlyT061 не выдаются за новый продуктовый пробел: product/fixtures/CSS/JS неизменны и deployedhashes совпали.

Read-onlyGitHub API подтвердил stableRelease06:00:39UTC и annotatedtag→exactsource. Русское body описывает изменения, CI/Full/CD/live, совместимость без миграций, сохранение macOS файлов, реальные ограничения и ссылкиPR/issues. Publicationattestation06:01:58UTC связывает release/tag/source с актуальным GO. Первый отказ attestation до записи из-за отсутствия буквального заголовка изменений сохранен сообщением оператора; добавление «Что изменилось» исправило только русский Release body, immutable records/code не менялись. Reviewer лично прочитал существующую успешную attestation и перепроверил ее decisiondigest.

### Честные незавершенные области

Обязательных технических gaps текущего выпуска страниц **нет**. Оператору остается отдельным docscloseout записать deployment/release audit и согласовать tasks/issues по доказательствам. Этот отчет не закрывает T048/T055/T056/T061 и не мутирует tracker/checklist. Их pendingmetadata не превращается в отсутствующую выкладку; фактический выпуск доказан выше.

Не закрыты этим заключением: вся человеческая/финансовая приемка F278/T011/T012/SC005/006, пять пользователей, реальное будущее автосписание/банк/возврат, установленный GRAFDev, количественная конверсия/удержание и желание каждого пользователя оплатить. CD сохраняет automaticretry/backfill/rangeplayback/normalizationcleanup как required_post_deploy в их собственных областях; они не названы фактически испытанными от healthycapability. Smoke outcome seed/proof skipped относятся к существующему необязательному продуктово-результатному сценарию CD и не являются skippedauthoritativegates текущегоFull.

### Отпечатки окончательного слоя evidence

| Доказательство | SHA-256 |
|---|---|
|CD execute |`ee9996dad860dde26241c873cb3c787d8883eb8adbd5177f63e6f1e5aea27617` |
|CD dry-run |`3c74f829a8e1980b311c5939ab90c0bc06c2b3e7f63abdbff0b50e867bb9b9a3` |
|Root runtime metadata |`04004b3005ed904bad1d3da54649a3ca7cd1ab56c5d8c0a949436004eff51fd5` |
|Root live acceptance |`1f15665361a2287f973759546a82778770042b48f1a85c2e5cdf0d18c3463279` |
|Distinct peer deployed file review |`93c9fa5f560b6c8b9ffa100f3cf1e3ee83aaad9566d821d3f003db1ceab95d7e` |
|Distinct peer public files |`acdd725d1be91eb958a86906dd08a9329d01f66c040f76de360054f7170f29f6` |

Окончательное решение передано оператору как независимый **TECHNICAL RELEASE PASS** для currente50c/v.04.5. Изменен только этот временный отчет; root может перенести его в последующий docscloseout без изменения frozen источника, runtime или immutable release records.


Оператор перенес только окончательный слой отчета; предварительный HOLD сохранен в истории. Чистота frozen источника относится к выпуску и publication attestation до отдельной документационной ветки. Текущая docs-only ветка не является развернутым исходником. Отметки задач и внешний tracker согласовывает оператор после этого независимого допуска.
