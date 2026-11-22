# T116 — независимая проверка конструкции теста HTTP control types

SCOPED TEST-CONSTRUCTION GO. Блокирующих замечаний к описанной конструкции теста и текущему draft стенда не найдено. Разрешён следующий тестовый этап существующей T116/#7444; production этим отчётом не принят. Сначала требуется фактический квалифицированный RED. Lane остаётся high-risk-product; это независимая проверка требований и конструкции, без выполнения продуктовых проверок.

Уточнение main во время ревью: полная native Release/Debug регрессия неизменённого source342, 53 проверки, готовится/выполняется отдельно через `/Users/yshishenya/Documents/graf-f200-regression342.KzxiQ7`. Её завершённого результата этот reviewer не получил и не принимает. Правка теста343, freeze, build и запуск343 должны ждать фактического завершения этой работы и подтверждённого отсутствия активных native jobs. Construction GO можно использовать сейчас; execution343 пока удерживается этим условием. Reviewer VM/jobs не запускал и завершения регрессии не ожидал.

## Проверенные предпосылки

Canonical: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`, branch `codex/200-windows-followup`, HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`, 234 записи dirty до отчёта. `.specify/feature.json` и read-only `check-prerequisites.sh --json --paths-only` указывают на `specs/200-windows-desktop-app`; физическая папка0309 не использована как источник фичи. В выводе prerequisites поле BRANCH содержит feature slug, фактическая Git-ветка проверена отдельно.

Прочитаны AGENTS/router, применимые правила codex-worktrees/spec-kit-flow/product-gates/release-and-validation/tracker-policy/github-issue-canon, действующие требования spec/plan/tasks/constitution, HTTP-разделы research/data-model/quickstart и local/packed custody contract. PRD local buffer policy сохраняет encrypted buffers, retention7days, device5GB, warning80%/critical95% и reserve min(10GB,10%); новый тест их не меняет. Current-product-status — история слитого продукта, не подтверждение текущей dirty Windows реализации. Применён code-reviewer для проверки реального пути, отказов и достаточности наблюдений. Новые Spec Kit стадии, hooks и issue sync не запускались: переиспользуется уже принятый scoped analyze на неизменных нормах.

Current scoped analyze `review-2026-10-10-protected-http-integration-gate.md` лично rehashed:
`51af545d0cc8a4dc31c5ea0d65595f08dcb6be2c8a4e2194ee3c3d8da90174e0`.
Его H1 prepare/full commit/adoption и H2 exact bytes/charged owner/budget остаются обязательными. Это reuse действующего requirements/analyze prerequisite, не новый общий analyze PASS.

Все девять нормативных файлов лично rehashed, таблица совпала с принятым analyze:

| Файл | SHA-256 |
| --- | --- |
| spec.md | b411bfb620e9d571422f9c423b0ae193ed70e87303d08e84a4b9844e32f81658 |
| plan.md | 9cdc5200419b6264d8e0c6a8c01aca5956b225661e674bba49acecbc4b90cf21 |
| tasks.md | 80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f |
| research.md | 4a7a1f9d8f7606a106b68e5b6194a0de8d75243508232c191f945f0fc0faa90e |
| data-model.md | c24b9d10bf5b935bcf51bb12034a0bb9ccef4a0b3719a138b48a26cbaa0d3bc7 |
| quickstart.md | 44c93c6558e8564aefe15a2180fd22d117f6368307d865b02253f9e0dffdf0b9 |
| contracts/windows-protected-local-custody.md | 598223854ea7e614694167c4019ef199e30c82b3ac1c44b33fcefa94fbe27fee |
| contracts/windows-protected-packed-custody.md | a1dedd9d5b7ce02e4a6c200a300b0423bcada82192217e2a79f9773428c4a7b5 |
| .specify/memory/constitution.md, от корня | d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859 |

Принятый baseline — `/Users/yshishenya/Documents/graf-f200-wipe342.fVaWAY/source.json`, SHA-256 `8f9cbf93de54af8d67eb8e03cba73f12598546da1646dcd822825c798a7fa62a`. Все209 entries лично сверены одновременно с canonical и frozen342: missing0, drift0 в обеих папках. Тест343 ещё не написан; текущая дельта209 относительно342 равна0. Нельзя выдавать этот снимок за уже подготовленный test343.

Предыдущий принятый отчёт `review-2026-10-10-custody-wipe-default-source-runtime.md` прочитан. Native342 receipt `d33e15f3d2bcb7d1e8ba8b9a44c5954e8b1ea0c2a1de8c007b97be093c1de4c9` и postflight342 `72002233436c70945a69dcfa630ee45adb1c726e829b8e34e0455b779751a902` лично rehashed и прочитаны. Их accepted stages — `default_wipe_green2_verified` и `source_binary_log_postflight_verified`; postflight связывает source342/native342 и209inputs. Это проверка сохранности accepted prerequisites, не повторная runtime приёмка342 или зависимых опытов341.

Tasks:120, done93, open27. T115 отмечена, T116 открыта; live OPEN и канонические метки #7444 переданы main в текущем поручении. Reviewer GitHub не опрашивал, не менял и отдельного live proof не заявляет. Нового task/issue либо изменения существующих требований нет.

## Все reviewer checklists

Просканированы все185 Markdown в checklists до этого отчёта. Прочитаны существующие пункты всех29 файлов с отметками и проверена их применимость к этому узкому допуску. Десять базовых requirements-файлов содержат154checked/0unchecked; остальные19 файлов с отметками —266checked/0unchecked. Ещё156 файлов не содержат checkbox items. Суммарно29marked/420checked/0unchecked. Ни одна отметка не изменена.

| Файл с пунктами | Checked | Unchecked |
| --- | ---: | ---: |
| advanced-routing.md | 14 | 0 |
| audio-capture.md | 24 | 0 |
| calendar-launcher.md | 5 | 0 |
| calendar-operation.md | 8 | 0 |
| calendar-wire.md | 5 | 0 |
| packed-writer.md | 12 | 0 |
| privacy-pause.md | 12 | 0 |
| requirements.md | 22 | 0 |
| review-2026-10-03-packed-tree-source.md | 38 | 0 |
| review-2026-10-04-calendar-join-gate.md | 12 | 0 |
| review-2026-10-04-calendar-resolver-gate.md | 12 | 0 |
| review-2026-10-04-calendar-url-gate.md | 12 | 0 |
| review-2026-10-04-manifest-cap-source.md | 9 | 0 |
| review-2026-10-04-packed-cadence-gate.md | 12 | 0 |
| review-2026-10-04-packed-cadence-source.md | 18 | 0 |
| review-2026-10-04-packed-live-writer-gate.md | 14 | 0 |
| review-2026-10-04-packed-live-writer-source.md | 9 | 0 |
| review-2026-10-04-packed-package-gate.md | 12 | 0 |
| review-2026-10-04-packed-reader-gate.md | 20 | 0 |
| review-2026-10-04-packed-reader-source.md | 9 | 0 |
| review-2026-10-04-packed-resize-gate.md | 14 | 0 |
| review-2026-10-04-packed-resize-source.md | 9 | 0 |
| review-2026-10-04-packed-rewrite-gate.md | 16 | 0 |
| review-2026-10-04-packed-rewrite-source.md | 9 | 0 |
| review-2026-10-04-packed-tail-gate.md | 14 | 0 |
| review-2026-10-04-packed-tail-source.md | 9 | 0 |
| review-2026-10-04-packed-writer-source.md | 18 | 0 |
| security.md | 27 | 0 |
| ux.md | 25 | 0 |

Requirements/security: тест не меняет account authority, wire/schema, ownership, диагностику, отсутствие plaintext fallback и общий кабинет. Audio/advanced-routing/UX: generated producers существующего fixture не получают полномочий реального устройства, не заменяют индикатор/Stop/AEC/installed parity. Packed/privacy требования и будущие T117/T118/T120 consumers сохраняются. Calendar пункты не затрагиваются этим тестом. Исторические SOURCE/runtime items, старые H1/H2/M1/M3 findings, отрицательные опыты и поздние исправления сохраняют свои исходные версии, результаты и область. Сводное420/0 не переаттестует их на source342/343 и не означает общий PASS приложения.

## Конструкция теста

Проверенный existing путь: `NativeCaptureStorageIntegrationTests.cpp:1114–1315` запускает ownedUpload через настоящий NativeCapture и resolver/adoption, подаёт3000 generated480-sample frames, дожидается реального finalizer и insertion commit/adoption generation1→2, выполняет shutdown/drain и освобождает прежнего владельца. Затем worker получает queue row и package через новый StoreOwner, освобождает внешний store, независимо читает expected logical bytes/hash, вызывает `inspectProtected` и `protectedUploadFromCold`. Нет READY setter, подставленного context/generation или настоящей сети/аудио/аккаунта. Это3000 десятимиллисекундных кадров, а не3000 отдельных PCM samples.

В `protectedUploadFromCold` подменяется только `ProtectedUploadSend`; real protected overload, `loadTracks`, `uploadPrepared`, `uploadFile` и protocol decisions остаются настоящими. Source342 подтверждает обычные std::string в DesktopHttpConfig/UploadRequest и вложенных identity/scope. Confirmed identity проверяется тем же transport, поэтому первый вызов именно cold send — GET sync-state, после loadTracks/hash; предварительные account GET внутри NativeCapture используют другой existing callback и не являются этим RED.

Принимается один новый oracle в начале cold send, до protocol branches: constexpr conjunction четырнадцати `std::is_same_v<std::decay_t<decltype(...)>, CustodyString>` для config.baseOrigin/workspaceId/deviceId/clientVersion/sessionToken, confirmedIdentity.userId/workspaceId, scopedAccount.userId/workspaceId и request.method/path/body/idempotencyKey/contentSha256. Поля optional identity/scope проверяются в unevaluated decltype; runtime dereference disengaged optional недопустим. Сравниваются типы фактических аргументов send, не специально созданный тестом charged DTO.

Marker `PROTECTED_HTTP request_config_types_charged=0/1 enforced=0/1` печатается из вычисленного результата; перед намеренным abort следует сохранить его через fflush(stderr). Единственный новый assert — `assert(!enforce || chargedControlTypes)` с диагностикой имени chargedControlTypes. Это runtime assertion, не static_assert/ошибка компиляции. Global test-only bool по умолчанию true, задаётся до worker launch, во время fixture не меняется. Default executable и прежний `--protected-upload` сохраняют enforcement. Новый `--protected-upload-control-types` отключает только этот assert; генерация, storage ACK/release/cold path, protocol responses, body/hash/range assertions, pressure tests, teardown и baseline accounting остаются теми же.

На source342 ожидается chargedControlTypes=false уже на первом sync callback. Control должен закончиться exit0 с прежним `actual_transport_bytes=pass` и новым `charged=0 enforced=0`; enforced запуск должен фактически закончиться exit3 с `charged=0 enforced=1` и именованным assert. Общий crash, timeout, compile failure, неверный marker или падение раньше этого места не квалифицируют RED. Старые byte/protocol checks не ослабляются и не заменяются проверкой типа. После будущего production исправления требуется charged=1 при enforced=1 и сохранение прежних assertions; данный RED-only harness не выдаёт будущий GREEN автоматически.

## Проверка draft стенда343

Прочитаны оба внешних файла целиком, а также helpers из accepted342 validate.ps1, которые prepare заимствует до первой строки `$old=ReadVerified`. `node --check` обоих mjs завершился exit0; сами prepare/run не исполнялись. В draft папке сейчас только prepare.mjs/run.mjs, без source.json/validate.ps1/native.json и тестовой дельты.

| Проверенный draft | SHA-256 |
| --- | --- |
| /Users/yshishenya/Documents/graf-f200-http343.oJnfkn/prepare.mjs | b7ee9ad4cfd8a24e81099d2530e15b3c5cb4d11b9c4817d6971dff06e79fb43e |
| /Users/yshishenya/Documents/graf-f200-http343.oJnfkn/run.mjs | 945be75405ea340da8680dd0266d94d90480bf8756f8db861aa1241fc57e1b40 |

Prepare перечисляет209inputs из342 и разрешает ровно один изменённый existing `apps/windows/Tests/GrafWindowsContractTests/NativeCaptureStorageIntegrationTests.cpp`; production/CMake/dependencies не включаются в delta. Source receipt и validate создаются CreateNew/wx. При нынешней нулевой delta запуск prepare ещё не допустим. Привязка к принятому342 означает именно три SHA source/native/postflight выше: native/postflight pins подставляются при prepare из файлов342, old source pin — при run; это вычисляемые pins, не уже существующая frozen343 квитанция. Изменение этих входов требует повторной сверки допуска.

Нативная последовательность проверяет accepted342 stages, idle, old native209, новые frozen209 и reserve≥11GB; копирует только разрешённый test delta, повторно проверяет209, собирает Debug существующего integration target и требует build exit0. Inherited InvokeOwned сохраняет actual process exit/completed, EXE SHA и Debug PDB SHA, stdout/stderr и log SHA. Control и RED идут последовательно из одного build; между ними нет rebuild или source copy. Обе записи binary/PDB должны совпасть при последующем принятии фактической квитанции.

TEMP вычисляется как `test-temp343-<name>-<configuration>`: control и types-red получают разные каталоги. Existing TEMP/log/receipt не перезаписываются. Control требуется exit0 и оба названных marker. Для RED обработчик принимает только исключение TEST_FAILED:types-red, затем отдельно требует completed=true, actual exit3, wrong-type/enforced marker и named assertion. Общий failure не повышается до expected RED.

После обоих запусков предусмотрены idle и source rehash native/frozen209; лишь затем native_completed=true и stage=request_config_type_red_verified. Timeout900000ms оставляет completed=false/native_completed=false, stage=timeout_requires_reconciliation, без Kill; terminal=true означает конец harness, а не завершённую native работу. Аварийный RED не выполняет C++ destructors: его TEMP сохраняется для дальнейшей отдельной сверки/очистки. Закрытие handle/тайм-аут не принимается за quiescence.

Run проверяет canonical/frozen343 source209, запас Mac≥80GB, hash исполняемого validate.ps1 и отсутствие прежней native.json. Нативный RequireIdle повторяется перед копированием и между опытами. Дополнительное указание main строже: не начинать даже правку/freeze343 до terminal completion полной регрессии342 и подтверждённого idle. Этот reviewer не проверял фактическое состояние VM и не выдал idle receipt.

## Граница допуска и остаток

Недостающих требований, блокирующих именно construction gate, не обнаружено. Написанный test delta, frozen343 manifest/harness, build/EXE/PDB, actual control0/RED3/log markers, terminal source209 postcheck и idle343 ещё отсутствуют; это следующие доказательства тестового этапа. Прежде них production остаётся на стопе. Отдельно отсутствует завершённый результат объявленной main полной53 native регрессии342; он нужен для снятия текущего запрета исполнения343, не для решения о конструкции.

Типовой oracle доказывает только соответствие четырнадцати exposed control string types. Название charged не означает измерения реальных allocations. Он не доказывает учёт API DTO/builders, промежуточных std::string, SHA/hex, ranges/vectors, LocalTrack/default filesystem path, allocator/control blocks/Debug proxies, native WinHTTP allocations или всей pipeline. Предложение будущего reuse generic strings, typed LocalTrack source, existing CustodyVectors и fixed-array SHA hex рассмотрено как контекст; ненаписанная production реализация не принята. Для неё остаются source/caller audit, реальные quota/failure/wipe проверки, native Debug/Release и отдельный review.

Transport marker сохраняет `protected_result_adoption=pending`: этот тест не выполняет protected scheduler prepare/result commit/adoption. Непустой prepare/full commit→dispatch, current-row/epoch fences, single result commit/adoption, lost poll/ambiguous/shutdown, part64KiB/4MiB/16MiB/resumed ranges и WinHTTP lifetime/error/cancel acceptance сохраняют собственные требования plan:1995–2105/quickstart:902–934. Global storageWritable/localQueueComplete остаются false. T116/#7444, T117 migration, T118 whole-pipeline/100cycles, T120 privacy, physical x64/AEC/60min SC-003, installed Windows/macOS parity и release остаются открытыми. Полный Windows parity не уменьшен до этого теста.

Единственная запись reviewer — этот новый append-only report с0checkbox. Изменения production/tests/spec/plan/tasks/markers/GitHub/VM/jobs/commits отсутствуют. До записи сохранён read-only hash inventory6077 tracked/nonignored paths для проверки отсутствия других изменений; финальная сверка выполняется после записи отчёта. Старые checklists и reports сохраняются побайтно.

Финальная сверка после создания: все прежние6077 paths имеют прежние hashes/состояние, изменённых0; добавлен только этот report. Checklist inventory186Markdown,29marked/420checked/0unchecked, report0checkbox; dirty234→235 только из-за нового файла. Ветка/HEAD прежние. Это проверка локальной сохранности, не VM idle/runtime proof и не принятие полной53 регрессии342.
