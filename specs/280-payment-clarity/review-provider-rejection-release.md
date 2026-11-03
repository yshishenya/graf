# Независимая проверка технического выпуска F280

Дата: 2026-10-02. Рецензент: `provider_rejection_requirements`, отдельный итоговый проход. Рабочая копия: `release-f280/crisp`, ветка `codex/280-payment-provider-rejection-closeout`, исходный HEAD `4591f90558565b8e1621bbfe931455f546ff6407`. Владение: только этот отчёт. Lane: read-only review технического выпуска `high-risk-product` / `release-deploy`.

**Вердикт: PASS технического выпуска v2026.10.02.1 и точности его границ. Новых CRITICAL/HIGH/MEDIUM/LOW замечаний0.** Полное закрытие F280, человеческая и финансовая приёмка этим PASS не подтверждаются. Выпуск уже опубликован; документационный PR и закрытие#7414 ещё требуют собственных ворот.

## Прочитанные источники

Прочитаны `release-provider-rejection-closeout.md`, `evidence/provider-rejection-release.json`, актуальные `tasks.md`, `validation-provider-rejection.md`, `converge-provider-rejection.md`; пять файлов `/tmp/graf-f280-provider-final-{runtime,public,installed-helper,stored-status,rollback}.json`; frozen candidate, train GO, decision, authoritative Full и publication attestation для окончательного кандидата. Отдельно прочитаны записи abandonment двух неуспешных кандидатов и существенные строки завершённых `/tmp/graf-f280-provider-final-full-native.log` и `/tmp/graf-f280-native-validation-pr-native.log`.

Повторных тестов, запросов к платёжному провайдеру, изменений БД, GitHub, коммитов или выпуска рецензент не выполнял. Выполнено только локальное чтение/сверка JSON и хешей, а также узкое чтение текущего GitHub Release и состояний пяти issues.

## Сверка доказательств

| Проверяемая граница | Результат |
| --- | --- |
| Exact source | Candidate/decision/Full start/end/requested/component SHAs/attestation/runtime совпадают с `4591f90558565b8e1621bbfe931455f546ff6407`. Три установленных source-file hashes в каждой службе совпадают с текущими байтами рабочей копии. |
| Frozen Full | `rc-20261001T224834Z-cddd2dfffe5e`, `github-full-36937258970`, authoritative_full=true, lanefull, statuspassed, skipped_gates=[], все component SHAs совпадают. |
| Full digest | Независимо вычислен SHA-256 исходного JSON: `sha256:75535f0aefb140cc8c7cd8777b4066337e56d96409f2a75dac3d00eae17c8ab2`; совпадает с decision/train/aggregate/rollback. |
| GO и decision digest | status/decisiongo, train `train-20261001T224746Z-4591f9055856`; SHA-256 исходного decision JSON `sha256:ba036779681d1c37c2e2f78ca36ae1bc946acf925880b333f5afe6ea39e6c161` совпадает с publication/rollback/aggregate. |
| Publication | Отдельная attestation связывает exact source/tag/decision. Свежий GitHub read подтвердил non-draft/non-prerelease `v2026.10.02.1`, targetCommitish exactsource, publishedAt `2026-10-01T23:02:02Z`. |
| Runtime | rec-api/processing/maintenance exactsource, running=true, checkout/public/production/expectedshop/observation=true. API/processing healthy, maintenancehealthnull честно не назван healthy. Aggregate совпал со всем finalruntime JSON. |
| Public | live/ready/download200; заново скачанный PKG9259700байт, SHA-256 `b5df859986d0ad36a07302c87c598b7a7d6e027a65e4024dd70fe0cba3338662`, preservedtrue. Aggregate совпал с finalpublic JSON; это сохранение прежнего публичного пакета, не новая сборка или установка приложения. |
| Deployed helpers | finalinstalled-helper совпал с aggregate: installed adapter/metadata/templatepass, providercalls0/dbcalls0; синтетический процесс отдельно от пользовательской HTTP-сессии. |
| Stored status | finalstored-status совпал с aggregate: две существующие403, READONLY/rollback, установленный predicate/templatepass, providercalls0. Это сохранённые живые данные и установленный код; авторизованное браузерное HTTP прохождение не заявлено. |
| Rollback | finalrollback совпал с aggregate/decision/Full; image resultdeployed, previoussource `216ab38e6eeb112aefa23f8c87cf69bf6f064b08`, statusnot_required_not_executed. Наличие guarded deploy/result не выдаётся за выполненный откат. |

## Неуспешные кандидаты и native gate

`rc-20261001T215108Z-ae3e8878c637` / source91b59ac8 / Full36931385550 и `rc-20261001T222514Z-1942bb89cf2a` / source95be4e11 / Full36934946364 имеют разные идентичности и собственные abandonment, deployedfalse. Они не совпадают с окончательным candidate/source и не участвуют в его passingFull. Историческая macos-diagnostic на source95be явно неauthoritative. Локальный изменённый focuscase был skipped и не принят за его прохождение.

В окончательном PR-логе изменённый `DesktopNotificationAccessibilityTests.testExplicitFocusFromInactiveAppDoesNotDependOnAnotherSuiteActivation` имеет started и **passed0.807с**; итог1191tests/2skip/0fail и ContractValidationPASS. В окончательном Full-логе тот же случай имеет started и **passed0.758с**; итог1191tests/2skip/0fail и ContractValidationPASS. Следовательно изменённый случай действительно выполнялся в обоих новых обязательных проходах; двух общихskip нельзя приписать этому случаю. Успех diagnostic/старогоSHA для этого вывода не использован.

## Допустимое закрытие и оставшиеся обязанности

T023/T024 завершены по синтетическому HTTP/SQL/DOM/security evidence; T025 завершён по новым exactSHA/Full/CD/runtime/publication. Исторические pending/FAIL записи в validation/converge/tasks явно помечены историческими, актуальное завершение вынесено в начало и отдельный closeout. Эти записи не смешивают прошлое ожидание с текущим результатом.

Свежий GitHub read подтвердил **OPEN**: #7414, F278#7285, umbrella#7366, T011#7378, T012#7379. В текущем tasks T011/T012 остаются `[ ]`. #7414 можно закрывать только после подробного русского closure comment и live closeout validator; этот отчёт не заменяет их. Документационный PR после добавления отчёта требует собственных актуальных governance-fast/macos-pr/pr-metadata checks и common validator.

Не доказаны: подключение recurring у магазина, настоящая разовая оплата сFalse, реальные списание/чек/банк/возврат, авторизованный браузерный HTTP путь после deploy, установленныйGRAFDev/полнаяT011, пять человеческих прохождений/конверсия/удержание. Сообщение пользователя об уже отправленном и рассматриваемом обращении вЮKassa фиксирует внешний статус, а не подключение услуги. В техническом отчёте нет основания объявлять эти критерии выполненными; они остаются открытыми.

## Дополнительная сверка окончательного текста и готовности закрытия

Прочитаны оба завершённых `/tmp/graf-f280-provider-final-dom-{chromium,webkit}.log`. На окончательном source `4591f90558565b8e1621bbfe931455f546ff6407` повторены шесть provider-rejection случаев recurring/generic/uncertain ×320/1280: Chromium6PASS/2deselected/44.91с, WebKit6PASS/2deselected/48.95с. Collection6/digest `0fc61c6feca5afe1c616d3cbb4b5f18507fece8824f325cca6f5efd2ff144b43` совпали в обоих логах и новом `final_local_browser_checks` evidence. Оба runner statuspass и isolated container removed. Это дополнительная проверка существующего localhost HTTP→SQL→DOM harness, без живого провайдера или production session; две deselected прежние promo-цепочки не названы пройденными в этом узком повторе. Старые8PASS/другойcollectiondigest сохранены как отдельный проход, counts не складываются.

`/tmp/graf-f280-provider-issue-proposed-validator.log` сообщает `issue-closeout: OK (live GitHub PR/run verification; acceptance criteria still require review)`. Новый раздел proposed_issue_closeout_validator правильно указывает#7414, expectedcandidate exactsource и actual_issue_still_opentrue. Это проверка предлагаемого closure comment, без утверждения о фактическом закрытии или замены приёмки. Фактическое закрытие остаётся последующим действием после документационного PR.

Окончательный документационный diff перечитан: актуальный completion добавлен к validation/converge, T025 отмечен выполненным с отдельной выпускной записью, T011/T012 остаются открытыми. Дополнения closeout/evidence точно соответствуют двум логам и предлагаемому validator; ограничения финансов/recurring/productionbrowser/human сохранены. Изменённых product/test paths в этом docs diff нет. Три production-файла отдельно сравнены с `git show <frozen-source>:<path>` и байт-в-байт совпали, включая окончательный template hash `9b428a4474355dc5357393773ad31fb382ecb90980f26c4e93d9f18c9737c0a9`. **Повторный PASS, новых замечаний0**. Последующие docsPR checks/commonvalidator и closurecomment/actualcloseout не подменены этим обзором.
