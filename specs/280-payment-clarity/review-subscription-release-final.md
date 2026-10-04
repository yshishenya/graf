# F280 — независимый окончательный обзор технического выпуска

## Итоговый аудит v2026.10.04.5

2026-10-04. Reviewer `/root/subscription_browser_final`, независимо от реализации и операции выпуска. Полоса: `release/deploy`; исходная работа F280 — `high-risk-product`. Ownership только этот временный отчет. Root перенесет его в отдельный документальный PR после приемки. Код, Git/GitHub, задачи, checklist, deploy, приложение и финансовое состояние reviewer не менял. Продуктовые наборы проверок не повторялись; чужие изменения сохранены.

**TECHNICAL RELEASE PASS — все обязательные технические ворота выпуска текущих страниц доказаны. Открытых критических, высоких и исправимых средних технических замечаний — 0/0/0.** Предварительные HOLD для прежних источников сняты этим самостоятельным окончательным аудитом. Закрытие задач/внешнего трекера выполняется оператором отдельно; технический PASS не приписывает финансовую, человеческую или установленную macOS приемку.

## Проверенная цепочка источника и выпуска

| Связь | Доказанное значение |
|---|---|
| Выпуск | `v2026.10.04.5`, опубликован `2026-10-04T06:00:39Z`, non-draft/non-prerelease |
| Frozen source | `e50c4a729cdb2cd4d1d9a59c27637410bcd8b908` |
| Опубликованная база | `.04.4` → `50e96292d96e36993436524c85829153feb27027` |
| Состав | `train-20261004T051702Z-e50c4a729cdb`, PR7535/7532/7536/7538 |
| Кандидат | `rc-20261004T053741Z-1af7d009d698`, frozen `05:37:41Z` |
| Authoritative Full | `github-full-37180461213`, full/passed, `skipped_gates=[]` |
| Full digest | `sha256:a5415006f6382f34875c1701637ccb9c7bee76cf22fa9e78ceb91ae16201835f` |
| Changelog digest | `sha256:17f61452481f741337d44c8a184fc7efef383795831195cc5577dcaab5c9a505` |
| Решение | Immutable decision и train-go относятся к тому же candidate/source/Full/changelog |
| Runtime | rec-api, rec-processing-worker, rec-maintenance — точный выпущенный source SHA |
| Annotated tag | `213e4ac66d21d7eb2ef3f104ad11fb63005a6abc` → точный source commit |
| Публикация | `pa-rc-20261004T053741Z-1af7d009d698`, `06:01:58Z`, тот же source/tag/decision |

Самостоятельно прочитаны candidate, train, train-go, canonical authoritative JSON, GO и publication attestation. Независимо вычисленные Full/CHANGELOG/decision digests совпали с соответствующими записями. Все requested/start/end/component SHA Full равны выпущенному источнику. Реальный линейный Git диапазон после `.04.4` содержит ровно четыре включенных PR. Frozen checkout на master был чист во время freeze/release attestation и соответствующего чтения reviewer. Сейчас root ведет отдельную ветку `codex/280-subscription-release-closeout` с документальными рабочими изменениями; ее HEAD/dirty состояние не являются новым runtime или изменением выпущенного source. Развернутый источник остается exact e50c.

После deploy самостоятельно пересчитаны **18/18 файлов** из `/tmp/f280-invoice-t061-final-hashes.json`: все совпадают. T061 requirements/source report SHA также совпали с merged-source acceptance. Каждый из **12 runtime hashes** сопоставлен с source manifest; шесть тестовых файлов проверены в исходниках и не выдаются за runtime. Отдельный независимый peer повторно подтвердил 12 deployed файлов, три публичных файла и все 13 критериев публикации/работы служб: `/tmp/f280-invoice-final-production-review.json`.

## Точные проверки PR и общий Full

Лично прочитаны common validator receipts и сопоставлены с текущим GitHub API:

| PR | Final checked head | Checked base → actual merge | governance / native / metadata run ID |
|---|---|---|---|
|7535 | `25fb7470e81a451ea3b9c18cedbfdff6c398a3c6` | `50e96292…` → `872d5b2d…` |37174915946 / 37174915938 / 37174916039 |
|7532 | `deb639ca8613daebfc31473ecc9418cdcaa1362f` | `872d5b2d…` → `498c9a29…` |37176667299 / 37176667451 / 37176666833 |
|7536 | `ad54ee020824a875aa5fe25aa7531b8d5ddb624b` | `498c9a29…` → `11d2b2d3…` |37177918864 / 37177918866 / 37177940583 |
|7538 | `9fd83a7cc597e1f0421170a8b3a31cc0ae88f7b4` | `11d2b2d3…` → `e50c4a72…` |37179198078 / 37179198054 / 37179197339 |

Все 12 run через текущий API — completed/success, attempt1, SHA совпадает с checked head. Receipts содержат proof и metadata digests. Prep/T061 receipts записаны до слияния и имеют merge=null; фактические merge независимо разрешены через API/Git. Старые d184/EOF результаты не используются как допуск final deb639. Подписка PR7506 уже вошла в опубликованную базу; новый train не выдает ее повторно за новое изменение.

Full37180461213 через текущий API — completed/success/attempt1 на exact e50c. Все 13 работ успешны: reserve, static/governance, strict/performance, macOS, восемь parallel shards и aggregate. Canonical evidence находится только в `.dev/ci-evidence/authoritative-rc-20261004T053741Z-1af7d009d698.json`. CD повторно использовал это доказательство; новый Full внутри execute не запускался. Diagnostic или failed receipt не переименован в authoritative.

История не скрыта:

- Full37178472845 на11d2 остается failure: старый тест моделировал открытие отсутствующим selector. T061 исправил только точный Help details selector: causal RED1→GREEN1, full touched file21PASS, requirements16/0, source0/0/0, пять assert AST nodes и parser сохранены.
- Full37179496922 наe50c остается failure по native timeout. Причина конкретного отказа **UNESTABLISHED**; последующий успех не объявляется доказанной причиной или flakiness.
- Diagnostic37180047879 success наe50c — диагностическая информация, не разрешение выпуска.
- Только новый authoritative Full37180461213 на новом candidate дал GO. Native/API/workflow/assertions/пределы T061 не ослаблены. Старые frozen/failed записи сохранены.

T060 requirements16/0, source/visual0/0/0 и их применимость уже независимо приняты. Доступность16×2 относится к неизменным шаблонам/CSS/JS/fixtures и обычному безопасному адресу; новые C0/DEL случаи подтверждены финальными202 contracts и22 actual GET. Final status56×2 выполнен на final guard. Эти наборы пересекаются и не суммируются. Общий Full проверил окончательный источник. Фактический converge находится в `converge-invoice-consistency.md`; отдельного `converge-invoice-t060.md` нет.

## Штатная выкладка и откат

Dry-run: candidate=go, candidate_gates=passed, local_ci=authoritative_full_reused. Execute использовал тот же source/candidate/evidence и завершился exit0 / deploy_result=pass / exact e50c, 243 секунды. Свежая backup `20261004T055148Z` — PASS. Секреты/permissions, DB identity, миграции/RLS, image capability/profile, Temporal/processing/media, dispatch и production smoke — PASS. Очищены34 синтетические записи и3 объекта; остатков нет. Temporal и processing readiness повторены после smoke — PASS.

Прочитанный exact CD source выводит deploy_result=pass только после persisted `finish deployed`, окончательной readiness и отключения rollback trap с deployment_complete=1. Текущая попытка завершена deployed; **откат не потребовался и не выполнялся**. Предыдущий успешный источник `.04.4` и новая backup доступны как fallback. Живой rollback или свежая полная restore rehearsal этим отчетом не заявляются: текущий CD явно вынес восстановление в отдельное расписание, сохраняя обязательную свежую backup каждой выкладки. Поэтому reviewer не добавляет вымышленное новое требование restoration drill для этой UI выкладки.

Compose предупреждение о неподдерживаемых secret uid/gid/mode сохранено; отдельные runtime permission/identity gates PASS. Warnings не названы отсутствующими и не подменяют успешный результат защитных проверок.

Runtime metadata root от05:57:35Z и distinct peer от05:58:13Z подтверждают три службы exact e50c и12 deployed product files. Public checkout, provider observation и all_workspaces — true. Reviewer лично прочитал и сверил доказательства; собственное повторное SSH чтение служб не заявляется.

## Публичные байты и live интерфейс

Reviewer самостоятельно повторно прочитал по HTTPS три публичных файла, вычисляя размер и SHA потоком без установки/запуска приложения. Каждый HTTP200; все совпали с `/tmp/f280-before-own-public-artifacts.json`, root и peer postdeploy проверками:

| Файл | Размер | SHA-256 |
|---|---:|---|
|graf-appcast.xml |6824 |`d62c4d7f0b28b6236fded564a0123510f9676038d1eb53ded77a25f90d832579` |
|GRAF-2026.10.04.4.zip |9513282 |`5a2c236260160f5ebcd3a695943f86ec08fc4558bf2bd437e76c4a0b95090c47` |
|graf.pkg |9259700 |`b5df859986d0ad36a07302c87c598b7a7d6e027a65e4024dd70fe0cba3338662` |

Самостоятельные live/ready GET дали HTTP200, statusok/statusready. Это серверный выпуск: сохраненные macOS файлы `.04.4` соответствуют scope, новую нотарификацию/установку этот выпуск не требует. Единственный GRAF Dev не запускался и занят другим срезом.

Лично прочитана `/tmp/f280-release5-live-acceptance.json` от06:00:16Z. Root через CUA и существующую авторизованную Zen session выполнил GET: intentional reload подписки, раскрытие условий, переход в историю и существующий оплаченный документ, раскрытие помощи, возврат на подписку. В подписке видны активность, оплаченный срок, состояние продления и renewal link; в документе — сумма, оплаченный период, чек, первоначально закрытые details и отдельные вопрос/возврат. Money mutation=false, private values retained=false. Это **фактическая live приемка основного оператора**, не собственное второе наблюдение reviewer частного кабинета. Она принята совместно с exact runtime hashes и независимой source/browser/actual GET приемкой.

Scope согласий точен: **новый checkout имеет предвыбор автопродления по решению пользователя; его можно снять и оплатить один период. Resume требует отдельного изначально снятого согласия.** Фраза peer temp report «во всех сценариях» не переносится как буквальное продуктовое правило; root исправил ее в tracked представлении. Код и условия этим документальным уточнением не менялись.

## Публикация и документы

GitHub API подтвердил stable Release06:00:39Z и annotated tag→exact e50c. Русское body описывает изменения, проверки, совместимость без миграций, сохраненные macOS файлы, ограничения и PR/issues. Attestation06:01:58Z связывает release/tag/source с GO; ее decision digest самостоятельно совпал. Первый отказ attestation до записи из-за отсутствия буквального заголовка изменений исправлен добавлением «Что изменилось» в Release body; immutable records/code не переписаны.

Прочитаны актуальные документы root: `docs/deployments/2brain-rec/release-v2026.10.04.5.md` и `specs/280-payment-clarity/release-subscription-clarity-closeout.md`. Они сохраняют точный развернутый SHA отдельно от будущего docs PR, backup, fallback, историю failed Full, ограничения live/operator приемки и сохранение macOS файлов. Фактическое закрытие issues не приписано до comments/validators. Отличий этих документов от доказанного технического выпуска не найдено. Peer финальный production JSON дополнительно содержит13/13 true; собственные12 runtime и3 public подтверждения отделены от root live acknowledgement.

## Остатки и границы заключения

**Технических gaps выпуска текущих страниц нет.** Технические критерии T048/T056/T061 достигнуты; запись checkbox, docs commit/PR и внешнее закрытие16 issues — отдельная последующая работа оператора. Этот reviewer не меняет маркеры и не заявляет уже закрытое GitHub состояние. Pending сверка метаданных не превращается в технический HOLD фактически опубликованного интерфейса.

Не закрыты этим аудитом: F278/T011/T012/SC005/006/umbrella, пять пользователей, реальные будущие автосписания/банк/возвраты, установленный GRAF Dev, количественная конверсия/удержание и желание каждого пользователя оплатить. Подготовленное письмо не отправляет запрос и не оформляет возврат. CD automatic retry/backfill/range playback/normalization cleanup сохраняются как required_post_deploy в их собственных областях; readiness/capability не выдаются за эти реальные сценарии. Необязательные outcome seed/proof skipped в CD не объявляются пропусками authoritative Full gates.

## Отпечатки окончательного слоя

| Доказательство | SHA-256 |
|---|---|
|CD execute |`ee9996dad860dde26241c873cb3c787d8883eb8adbd5177f63e6f1e5aea27617` |
|CD dry-run |`3c74f829a8e1980b311c5939ab90c0bc06c2b3e7f63abdbff0b50e867bb9b9a3` |
|Root runtime metadata |`04004b3005ed904bad1d3da54649a3ca7cd1ab56c5d8c0a949436004eff51fd5` |
|Root live acceptance |`1f15665361a2287f973759546a82778770042b48f1a85c2e5cdf0d18c3463279` |
|Peer deployed file review |`93c9fa5f560b6c8b9ffa100f3cf1e3ee83aaad9566d821d3f003db1ceab95d7e` |
|Peer public files |`acdd725d1be91eb958a86906dd08a9329d01f66c040f76de360054f7170f29f6` |

После записи reviewer повторно сверил source18/runtime12 и перечитал итог. Изменен только этот временный отчет. Окончательное независимое решение: **TECHNICAL RELEASE PASS для e50c/v2026.10.04.5**, пригодно для переноса root в отдельный docs closeout без изменения frozen/runtime/immutable записей.


Оператор перенес окончательный слой завершенного отчета; предварительный HOLD сохранен в истории. Отметки задач и внешний tracker согласовывает оператор после этого независимого допуска.
