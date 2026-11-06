# Round258: требования к защищённому AAC job-потребителю

## Решение и точная область

**REQUIREMENTS GO только для предложенной bounded native AAC prerequisite.**
Это допуск к RED/реализации `LocalRecordingPackage::readProtectedPlayback`,
не SOURCE GO, не принятие semantic inspector, приложения или T116/#7444 целиком.
Lane: существующий high-risk-product; независимый scoped `speckit-analyze` и
ограничения `speckit-implement`. Старые отчёты и checklist markers неизменны.

Принято именно предложение main: trusted root + настоящий
`shared_ptr<const ProtectedCustodyPackagePair>` + заявленная длительность +
общий ненулевой cancellation; результат `CustodyFileResult<PlaybackEvidence>`
содержит только `decodedFrames` и `containerDuration100ns`. Нет normal,
playbackAvailable, upload/delete capability, пути, URL или сохранённого proof
для позднего использования. Старые path-based `inspect` callers не получают
full decode. Отдельный потребитель настоящих protected readers допустим как
последовательный prerequisite по plan, но неподключённый prerequisite не
считается защищённым приложением.

**REQ257-B1 не закрыт для старых scan/open/upload путей.** Его запрет не
распространяется на этот новый ограниченный codec-вызов с реальным owned input
и job boundary. Полный inspector/manifest/privacy/account/bootstrap/effect
adoption остаётся **NOT GO / не реализован**. Никакого dummy account context
для получения codec evidence не требуется: вызов не отображает данные, не
меняет owner/queue и не выдаёт capability. Account/session/epoch gate §7 нельзя
обойти при последующем принятии результата или любом продуктовом действии.

## Нормативная инвентаризация

До нового отчёта: **109 .md**. Десять действующих нормативных списков имеют
**154 checked / 0 open**; их критерии прочитаны лично. Остальные 99 — исторический
контекст: 95 прежних файлов (**256 checked / 10 open**), два Round256 и два
Round257 отчёта без checkbox. Исторические open не переименованы в новые
обязательства; старые PASS не принимают Round258.

| Действующий список | Checked / open |
| --- | --- |
| advanced-routing.md | 14 / 0 |
| audio-capture.md | 24 / 0 |
| calendar-launcher.md | 5 / 0 |
| calendar-operation.md | 8 / 0 |
| calendar-wire.md | 5 / 0 |
| packed-writer.md | 12 / 0 |
| privacy-pause.md | 12 / 0 |
| requirements.md | 22 / 0 |
| security.md | 27 / 0 |
| ux.md | 25 / 0 |

Immutable inventory SHA256 старых109: сортированные строки
`repo-relative-path + space + file-SHA256 + LF`:
`bec683a8dcc0f02d178c73e7d5a5f1d39ee0537ff59aca9a4bf8f77b12da2d6f`.
Tasks: **120 total / 93 closed / 27 open**; T116–T118/T120 не закрываются.

## Scoped analyze: условия принятого предложения

Основания: Constitution I/IV/VI; spec FR-011/012/021/022, SC-001/003/006;
plan «Актуальный порядок: независимый срез хранения» и packed dependency
step5; local custody §5–7, packed §6.1; quickstart §12; requirements/security,
packed-writer CHK001/009–012, privacy-pause CHK007–012, UX truthfulness.
Currentness самого immutable input отличается от текущего права аккаунта.
Публичная structural value или future owner не заменяют реальный Pair.

| Область | Обязательное значение этого GO |
| --- | --- |
| Provenance / phase | Только private-ctor Pair из настоящего защищённого чтения; current selected phase sealedNormal/sealedDegraded, exact SEALED playback ref. Capturing/finalizing/discardPending, null input и LIVE playback не дают evidence. SealedDegraded разрешает codec-проверку, но не означает проверенный degraded prefix. |
| BOTH slots / members | `openProtectedCustodyReaders` проверяет обе физические metadata slots и все sibling refs, actual representation/version/length/hash и сохраняет всю группу владельцев. Любой плохой sibling — общий отказ; no old-slot rollback. Здоровый LIVE peer проверяется по batch contract, не принуждается стать sealedNormal. |
| Реальный job | Общий `CustodyNativeJob <=4` захватывается до native работы и живёт до actual release всех MF/COM объектов. Batch, packed verification и hash уже получают собственные admission: вложенность не обходить и не заменять фиктивным счётчиком. Исчерпание — typed quota failure, не ожидание UI или success. |
| Retention / cancel | Pair, BOTH-slot readers и общий cancel удерживаются по значению весь вызов. Null/true cancel отвергается до IO. Проверки до/после native waits/Get/ReadSample/buffer и непосредственно перед успешным возвратом. Timeout/cancel не освобождают ещё работающие объекты; зависший native call не получает выдуманную wall-time гарантию. |
| Native input | IStream -> MFCreateMFByteStreamOnStream -> MFCreateSourceReaderFromByteStream. Только audio stream0, AAC48kmono; отсутствие stream1 доказано именно MF_E_INVALIDSTREAMNUMBER. Не URL/temp/plaintext fallback, не production container parser и не re-encode. |
| Config / выход | Документированная HEAAC extra + известная ASC0x1188, raw payload, struct/reserved и согласованные optional attrs; не произвольный profile-level magic byte. Запрашивается только PCM subtype, без rate conversion/downmix. Фактический выход PCM16mono48k/block2/avg96000 проверяется, изменения/неизвестные формы отвергаются. |
| Полный decode | Проверяется каждый sample, включая sample с EOS; допустимы только flags0/EOS и actual stream0. Native error, type change, tick, unknown flags, null без EOS, empty/misaligned sample не success. Настоящий EOS при нуле суммарных кадров — отказ, не подтверждение AAC. |
| Время / прогресс | Nonnegative actual sample timestamp/duration, отсутствие регрессии/дыр; contiguous в пределах квантования одного sample, не нового допуска100ms на каждый пакет. Проверки переполнения до арифметики/использования. Непустой sample увеличивает ограниченный frame count, без бесконечного no-progress цикла. |
| Границы длительности | duration input положителен, арифметически представим; `(manifestDurationMs+100)*48` проверяется до сложения/умножения. Positive container duration и counted PCM duration независимо <=100ms от заявленного значения, без расширения округлением. Значение caller — bound/comparison, не доказательство manifest или права на запись. |
| Память | Нет накопления всего PCM, собственные байты проверяются/учитываются до выделения; native buffer size проверяется до Lock/копирования. Сохраняются owned64MiB, native job2MiB, cache2MiB, pins32, chunks256KiB. MF internal allocations отдельно измеряются; отказ allocation не маскируется semantic corruption. |
| Shutdown / error | Sample/buffer/type/reader/byteStream освобождаются до MFShutdown/CoUninitialize; pins/readers/Pair живут через весь native shutdown. Typed ошибки сохраняют точный HRESULT; cancel/native failure/invalid content не объединяются в ложный успех. Result — только два scalar, без позднего owner reuse. |

Нет CRITICAL/HIGH противоречия требований для **этой** readonly codec-границы.
Полная normal/degraded/short/manifest/privacy authority намеренно не входит:
exact protected manifest/hash/session binding, trusted cleaned prefix/reason,
short stop/no-fault/frame predicate, Mac11keys/ISO/optional omission и64KiB,
owner/epoch/effect revalidation требуют отдельного concrete inspector proposal.
Список записей не получает full collection decode или normal/play authority
из metadata projection. Нового продуктового лимита длительности, согласия,
профиля AAC или правила удаления данным решением не вводится.

## Native AAC: предел доказательства

Уточнение main принято для RED/кода в existing `LocalRecordingPackage.*` и
native ветви existing `ProtectedCustodyFilesTests.cpp`, без нового target.
Mechanical test-scope correction: здесь уже есть native `Fixture` с trusted
root/user-only DACL, настоящий private Pair и TU-local `afterRead` для отмены.
Их reuse подтверждён личным чтением; setup/fault mechanism не дублируется.
`ProtectedCustodyPackageTests.cpp` проверяет structural codec, не заменяет эту
native fixture. Это уточнение места теста, не расширение production GO.
Known USER_DATA ровно14B: WORD payload0; WORD profile `{0,0xFE,0x29,0x2A,0x2B}`;
WORD struct0; WORD reserved1=0; DWORD reserved2=0; ASC `0x11,0x88`.
Optional MF profile, если присутствует, совпадает с WORD profile; optional
payload, если присутствует,0. Отсутствие optional attribute — только штатный
`MF_E_ATTRIBUTENOTFOUND`, не произвольный HRESULT, неверный тип или native failure.
Unknown/HE values, в том числе0x2C/0x2E–0x33, отвергаются. Значения0/0xFE —
документированное отсутствие profile indication, не самостоятельный LC proof.
Таблица Microsoft различает AAC0x29/0x2A/0x2B и HE profiles; это не требование
одного magic byte. [AAC Encoder](https://learn.microsoft.com/en-us/windows/win32/medfound/aac-encoder),
[AAC Decoder](https://learn.microsoft.com/en-us/windows/win32/medfound/aac-decoder).

Microsoft описывает первые12B `MF_MT_USER_DATA` как HEAAC extra, затем ASC.
Двухбайтовая ASC бывает и у AAC-LC, и у HE-AAC с implicit SBR/PS: только
ASC не доказывает отсутствие этих tools. Поэтому существенны фактический
decoder output, отсутствие принудительного преобразования и отказ при change.
Это native configuration/decoded evidence, не собственный bitstream parser и
не универсальное доказательство отсутствия любой скрытой AAC extension или
обнаружения любой порчи. [AAC Decoder](https://learn.microsoft.com/en-us/windows/win32/medfound/aac-decoder),
[AAC Media Types](https://learn.microsoft.com/en-us/windows/win32/medfound/aac-media-types).

Round257c: MF достиг EOS, но дал0PCM frames. Не утверждать HRESULT decoder
error; конкретный counterexample требует positive counted duration. Hash
доказывает exact retained bytes, decode — наблюдённую декодируемость/выход.

## SOURCE/испытания — ещё не приняты

Main сначала RED в существующем native ProtectedCustodyFilesTests: настоящий
protected generated AAC + private Pair + BOTH readers; исходный positive;
тот же damaged mdat с корректным новым SHA должен быть rejected из-за0PCM.
Нужны pre/mid-stream cancellation и late-cancel перед return,4-job exhaustion
и release/retry, bad sibling, native formats/extra streams/flags там, где есть
реальные fixtures. Невоспроизводимые native cases честно NOT RUN, не mock PASS.
Проверить ошибочные ранние выходы и actual release/admission, не только1s success.

Последовательные native focused Release/Debug, SDK/portable выполняет main;
reviewer ничего не запускает. Representative duration/30s и collection/job
memory/CPU/cancel/shutdown измерения нужны для SOURCE/performance evidence;
generated1s не принимает SC-003, hardware, установленный клиент или full T118.
Round257 old-path RED сохраняется и не переименовывается в GREEN. Решение
требований не доказывает, что новая реализация уже существует или прошла тесты.

## Exact baseline

Canonical `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
branch `codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; dirty preserved.
Supported read-only prerequisite подтвердил active feature200.

| Файл | SHA256 |
| --- | --- |
| constitution.md | d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859 |
| spec.md | b411bfb620e9d571422f9c423b0ae193ed70e87303d08e84a4b9844e32f81658 |
| plan.md | 527e660d9e1682e7a0f0a79118ea4bab38d4c174542b49c0113f571528a5b89c |
| tasks.md | 80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f |
| quickstart.md | fc225d2ec40cc26a7fad0bc6d7adcb22d7f4d676fcdf70b2e645dbbdb06ddb8e |
| data-model.md | 8dd54012c3bfe4003cd18db98ebc67e0b7730cbbdfb6523b881cce4cdc15ec19 |
| windows-protected-local-custody.md | ec93d11c474cb970d57c2324518d541cd9fb3e7bb7f2f807d63d612ad878624a |
| windows-protected-packed-custody.md | a1dedd9d5b7ce02e4a6c200a300b0423bcada82192217e2a79f9773428c4a7b5 |
| LocalRecordingPackage.cpp | 38b709c9a184ac586b1112cf934e4bfbada400815202eaad34aa463fda13b859 |
| ProtectedCustodyMetadata.h | 3e1f12fda3e18463c6430921e16173afac5c549aaebfa222efcc9dd24b743478 |
| ProtectedCustodyReader.h | 98f688c86b0499549baec78a7ef2a225c3c80ba20754ee1fe1d9c650d399cc94 |
| ProtectedCustodyReader.cpp | c6de956a7c546647afddc910fa3dd0b153d731ecb354c974b81fb8b51752767d |
| ProtectedCustodyMemory.h | a5a67fb3448f07d4232cf8dee893e60e65c3eea5687a0908f4469226be2000ad |
| NativeHashFailureTests.cpp | a2d6d9a8e1dd0ea75832d987502b4cfd6a41cfd0414e6506c60ea933cc8f3f76 |

Reviewer write scope: только этот новый отчёт. No code/tests/spec/plan/tasks,
old reports, GitHub, VM, app/profile, commit или release changes.
