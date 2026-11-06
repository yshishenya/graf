# Round255b — независимая проверка исходников общей границы формата

Дата: 2026-10-06. Feature200, T116/#7444, `high-risk-product`.
Только `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
ветка `codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`, dirty.
Основание: лично прочитанный `review-2026-10-06-package-format-gate.md`,
REQUIREMENTS GO15/15, SHA256
`b712a972476d30f3ffc07b0ecd2c848c071e4815e71d8c761a3b35eca1fcc2d0`.

## Промежуточное решение

**Проверка кода завершена: CRITICAL0/HIGH0/MEDIUM0/LOW0 в узком diff пяти
файлов. Окончательный SOURCE пока PENDING: ожидается перечитка терминальных
квитанций с actual source и EXE hashes.**
Release и Debug 255b имеют переданные основным исполнителем завершённые
4/4 PASS; reviewer сам Windows-команды не выполнял и квитанции из Windows
не извлекал. SDK build также передан как успешный. Полный Windows50 ещё
выполняется. Эти состояния не заменены предположением об успехе.
Проверка кода не выявила причины менять принятую формулу, добавлять задачу,
новый decoder/schema/adapter или ослаблять прежние Windows assertions.

## Неизменный снимок 255b

Все пять diff лично прочитаны целиком относительно сохранённых копий
`/tmp/graf-f200-format-baseline.Cgqb5G`; отдельно прочитаны helper,
производственные callers и окружающие native/portable тестовые ветки.
Текущая область именно 255b, не неудачная сборка 255.

| Файл относительно apps/windows | Frozen255b SHA256 |
| --- | --- |
| `RecApp/Recording/LocalRecordingPackage.cpp` | `38b709c9a184ac586b1112cf934e4bfbada400815202eaad34aa463fda13b859` |
| `Tests/GrafWindowsPackageTests/V5LocalRecordingWriterTests.cpp` | `e5b932d59cad05f7906e420329ebf1b01b447817a18f88b9892c4e74169eeef3` |
| `Tests/GrafWindowsCoreTests/NativeHashFailureTests.cpp` | `65035b070a2ce26e10a3dca51d5af4b24c3c59d9e7d3da131b435bf96fdc4fc4` |
| `Tests/GrafWindowsCoreTests/CaptureFaultStateTests.cpp` | `fcb243525e05630ad418956a36e6b6b6fd97be58ccb3cb981284e257c4acef91` |
| `Tests/GrafWindowsContractTests/DesktopUploadRecoveryTests.cpp` | `480e8fd4a744188215e019c3feb9e351de325a512fffc00c60f7ba1032aeac42` |

Manifest вне Git в `/Users/yshishenya/Documents/graf-f200-calendar-test.UjB7WI`:

| Manifest | Входов | SHA256 | Личная сверка canonical / Mac mirror |
| --- | --- | --- | --- |
| `source-format-round255b.json` | 171 | `b65dbdcb738cfa7cccb8673df2c21d219ad9f45f154e636d07fda9548ba547aa` | 171/171 и171/171 MATCH |
| `source-sdk-format-round255b.json` | 178 | `1148d5d0d0eff4a220292850ef2bf4302e0aaf11f1d6748b9fd36a29194d0fd6` | 178/178 и178/178 MATCH |

Это сверка исходников на Mac, не утверждение о лично прочитанных Windows
EXE. Сохранённые baseline SHA пяти файлов приведены в requirements report.

## Реальная общая граница и сохранённые полномочия

`LocalRecordingPackage.cpp:157–170`: один `playbackValid` вычисляется через
прежний `playbackMatches && canonicalPlayback`. Normal/valid требует этого
результата независимо от explicit root. Degraded остаётся degraded при
прежних media/hash условиях, даже если его playback не прошёл AAC проверку.
UI по-прежнему требует `!custodyRoot.empty() && playbackValid`.

| Проверенное свойство | Решение по исходникам |
| --- | --- |
| Normal fake AAC с правильными bytes/SHA | Отказ malformed; hash больше не является достаточным основанием normal. |
| WAV/hash/confinement | Прежние matchesArtifact и canonicalWav обязательны; parsing и bounded exact shape не менялись. |
| Retained/degraded/prefix | Старая формула retained/status/reason сохранена; не normal, не удаляется; настоящий AAC может быть playable. |
| Длительность при плохом playback | Valid WAV продолжает давать durationMs; неподтверждённая тишина и wall-clock padding не добавлены. |
| Legacy/time/UUID | Старый manifest, optional bounds/drop-invalid-time и прежняя caller identity политика не изменены. |
| Portable/MF unavailable | Helper portable=false; native open/type/duration отказ не даёт normal fallback. Windows N отдельно не испытана. |
| Один результат/место проверки | Helper открывается не повторно ради UI; новый параллельный validator отсутствует. |
| Потоки выполнения | Callers остаются transport/worker; IO не перенесено в capture callback или UI thread. |

Все production inspect call sites повторно найдены:

- `DesktopHttpTransport.cpp:149`: rootless packageTracks, только valid;
  тот же guard в packageTrackBytes:551 и upload:1009; отказ invalidPackage:1013
  предшествует первому send.
- `AppMain.cpp:1963`: worker scan с custody root.
- `AppMain.cpp:2178`: worker open с root, до прежней UI передачи.

Таким образом исправляется существующий rootless upload bypass, а не только
UI playback. Вызовы и public API не заменены.

## Сохранность тестов, не только новые assertions

| Набор | Лично проверенное сохранение/добавление |
| --- | --- |
| V5LocalRecordingWriterTests | Fake encoder остаётся RAW writer/hash/finalize/idempotence proof; inspect fake теперь malformed с root и без, upload invalidPackage/sends0, файлы сохранены. Native real1s AAC подтверждает rootless valid/notplayable и explicit-root playable; legacy без времени/status и invalid time/zone сохраняют positive valid/drop-invalid semantics. |
| V5 duration regression | Настоящий2s AAC копируется в пакет с canonical1s WAV, правильными bytes/SHA обоих артефактов. Оба root режима malformed, WAV duration1000 сохраняется; upload sends0. Это изолированная duration ошибка, не неверный hash/WAV header. |
| V5 retained/degraded | Прежние native degraded/playable и corruption отказ, interrupted/fake prefix retention, constructor/destructor, nonfinite/frame/duration/confinement/symlink проверки не удалены. |
| NativeHashFailureTests | Default native encoder/100frames вместо fake; sends1/creates3/destroys3 и create3 failure invalidPackage/sends0/creates3/destroys2 сохранены буквально. Reset faults, будущий hash, provider open/close/property assertions не удалены. |
| CaptureFaultStateTests | Windows scenario0 использует прежний native encoder, 3000frames/30s policy не уменьшена. Старое valid iff scenario0, policy/generation/finalizer/queue/restart проверки остаются. Portable writer/state доказательства сохраняются, fake inspect не объявлен valid. Mock recovery не считается реальным transport format proof. |
| DesktopUploadRecoveryTests | Оба Windows positive fixtures — default encoder/100frames; прежние status/reason/retryClass/ranges, create/session/manifest/media/playback/finalize/sync, restart/no-requeue/owner/exact bytes/local removal assertions исполняются Windows. Нет Windows skip или раннего возврата перед матрицей. |
| Portable recovery | Ранний возврат только non-Windows: реальный transport отказывает invalidPackage до send, duration/bytes сохранены. Server-stage и sync positive матрицы portable больше не доказывает; обязательны Windows executions, не подмена тестов одним отрицательным сценарием. |

Изменённые fake valid assertions заменены честными отрицательными; прежняя
positive legacy/time/status совместимость дополнительно сохранена на реальном
AAC. Не обнаружено удаления прежних Windows wire/CNG/state assertions ради
нового guard. Тестовые артефакты генерируются прежним encoder; нового helper,
knob, зависимости или committed media нет.

## Переданные результаты выполнения — отдельная атрибуция

Далее сообщения основного исполнителя, а не запуски reviewer. Идентификаторы
терминалов сохранены как локальные ссылки на evidence; их содержимое и EXE
hashes ещё требуют окончательной перечитки.

| Выполнение | Переданный результат |
| --- | --- |
| Initial portable RED `c02c7a` | Behavioral assertion49, 0.44s; old production, не ошибка среды. |
| Initial native RED `f0ba5e` | Behavioral assertion49, 2.12s; receipt `C:\Temp\graf-f200-format-round255red.json`, test_exit8. |
| Portable focused `021e29` | 3/3 PASS, 7.96s. |
| Portable full `3207bb` | 46/46 PASS, 21.58s; не native AAC/wire proof. |
| Native255 `373368` | BUILD FAILED, /WX C4456: loop index затенил прежний index; runtime NOT RUN. |
| Native Release255b `8229a7` | configure/build/test0, exit0,4/4 PASS24.38s; Capture9.98s, Recovery13.66s,V5 0.57s,Hash0.17s. Receipt `C:\Temp\graf-f200-format-round255b.json`. |
| Native Debug255b `095ed6` | configure/build/test0,4/4 PASS28.48s; Capture10.95s,Recovery16.56s,V5 0.63s,Hash0.31s. |
| SDK255b `f31090` | restore/build0,exit0; actual AEC3 identity `846fe90a289f58b7c9303a635142aa2c7caa93e5`. Старое D9025 предупреждение не позволяет утверждать сборку без предупреждений. |
| Full Windows255b50 | Выполняется; NOT YET ACCEPTED. |

Исправление 255→255b — только имя `audioFrame` в native test loop: проверка
append100frames и остальные assertions прежние. Старая failed255 запись не
переименована в PASS. Frozen manifest уже содержит новое имя и SHA.

Лично прочитан `validate-format-round255b.ps1`: create-once guard, проверка
mirror и actual171 source hashes, отдельные четыре EXE hashes после сборки,
CTest regex всех четырёх целей, Release, последовательный `-j1`, timeout300,
terminal/exit запись в finally. Скрипт не является доказательством фактического
выполнения; для финального SOURCE нужны сами завершённые квитанции и вывод.

## Ponytail и незакрытые границы

`ponytail-review`: **Lean already. Ship.** Только оценка сложности:
production3 additions/2 deletions, reuse существующего helper. Нет безопасного
удаления полезных assertions или новой ненужной абстракции. Эта формулировка
не разрешает выпуск/установку и не заменяет независимую приёмку.

Прежний canonicalPlayback проверяет metadata AAC48kHz/mono и presentation
duration<=100ms разницы. Он не читает payload до EOF, не удостоверяет отдельно
AAC-LC profile, decoded content или stream closure. Эти доказательства здесь
не заявлены. Существующие plaintext URL/reader и TOCTOU границы не объявлены
новой защищённой интеграцией. Full T116 producer/consumer/admission/recovery,
T117 migration, T118 acceptance, H250 working-profile install/launch NO-GO,
physical x64/60min/AEC/accessibility/signing/clean install/update/rollback и
auth-upload E2E остаются отдельными незавершёнными обязательствами.

Reviewer не менял production/tests/spec/plan/tasks/GitHub/VM/devices,
не запускал сборки/тесты/приложение и не делал commit. Единственная запись —
этот новый reviewer-owned report. Старые checkbox/report hashes должны
сохраниться104/104; новые checkbox markers в этом отчёте0. Итоговая сверка и
принятие актуальных runtime receipts будут добавлены ниже без переписывания
истории неудачной 255 сборки.

### Контроль сохранности промежуточного отчёта

Лично перечитан весь новый отчёт. SHA256 всех104 прежних checklist/report
совпал104/104, mismatch0; requirements report сохранён. Tasks SHA256
`80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`
не изменился. `git diff --check` PASS. Новых checkbox markers0.
Иные dirty правки основного исполнителя не сбрасывались и не редактировались.
При финальной передаче квитанций дополнительно прочитать только добавленные
Round255 execution notes, final format quickstart и owned F200 release notes;
сверить факты и незакрытые T116/SC-003/AAC-LC границы. Финальный SOURCE
остаётся PENDING до такой перечитки и actual runtime identity проверки.

### Дополнение — личная проверка текущей документации Round255

До завершения Windows50 лично прочитаны текущий раздел Round255
`validation-2026-10-02.md:10557` целиком, новый раздел
`quickstart.md:851–868` и только owned YAML entry
`release_notes_round255_shared_package_format` (`F200.yaml:1856–1867`).
Замечаний к фактам и обозначению незавершённых этапов в этих разделах:
CRITICAL0/HIGH0/MEDIUM0/LOW0. SOURCE verdict остаётся PENDING.

- Validation различает behavioral RED, parser/setup отказы до теста,
  failed255 C4456 и successful255b. Новые пять SHA и два input manifest SHA
  совпадают с независимо проверенным frozen255b снимком. Полный Windows50,
  actual source/EXE reread и SOURCE явно PENDING.
- Release/Debug4/4 и portable46/46 согласованы с переданными терминальными
  результатами; SDK/AEC3 указан отдельно, D9025 warning не скрыт.
  Предшествующее YAML упоминание50/50 находится вне нового round255 entry
  и не принято здесь как успех нынешнего Windows50.
- Quickstart называет все четыре native suites, positive real encoder,
  оба root режима и отказ до send; portable покрытие не выдано за AAC/wire
  matrix. Сохранность WAV/degraded не заменена удалением повреждённого пакета.
- Полные FR-011/SC-00360min, AAC-LC/payload/EOF, защищённая интеграция
  T116, migration T117, acceptance T118 и working-profile H250 не закрыты
  этими формулировками. Новый codec/schema/task, установка или выпуск не
  заявлены. Tasks SHA по-прежнему совпадает с исходным120/93/27 снимком.

Снимок документов этой перечитки (целые файлы, не только owned sections):

| Документ | SHA256 |
| --- | --- |
| `validation-2026-10-02.md` | `300d74506783c48544eecac02fa9be2140f4b99e5473b7234651ad8df175f39a` |
| `quickstart.md` | `bfb69e14ccf1fa01cd2e6f31bb6ac3df995e25cd0fa807cdb1fdaa8b1de2abe3` |
| `changes/unreleased/F200.yaml` | `76505addc8b39afd49adc9a6dd5c3dfd5afeb1a11574a6eeb7bd1caa11764eb0` |

Лично прочитан вне-Git `read-all-round255b.ps1`, не выполнен reviewer:
он проверяет terminal/phase/build/test, actual NTFS и mirror input hashes,
четыре группы EXE (Release focused, Debug focused, full Release, SDK), затем
экспортирует квитанции с SHA сверкой и отдельную RED/build-failure историю.
Наличие каталога или отдельных экспортированных JSON ещё не означает успех
всей перечитки: для принятия нужны завершающий
`ROUND255B_FULL_ACTUAL_SOURCE_EXE_REREAD=PASS`, полный набор квитанций и
их личная проверка. После финального append исполнителя документация и
runtime evidence проверяются снова; этот промежуточный снимок их не заменяет.

## Окончательное решение 255b — SOURCE и scoped DOCS GO

**SOURCE GO — 15/15 принятого узкого requirements scope;
CRITICAL0/HIGH0/MEDIUM0/LOW0. DOCS GO для трёх owned Round255 sections.**
Предыдущие PENDING записи выше — история промежуточной проверки, не текущий
вердикт. GO относится только к общей normal-format correction и её пяти
исходникам frozen255b. Full T116/FR-011/SC-003, H250 и установленное приложение
остаются NOT GO; этот отчёт не является разрешением выпуска.

### Личное чтение экспортов и точная атрибуция

Reviewer лично загрузил и разобрал все шесть JSON целиком из вне-Git каталога
`/Users/yshishenya/Documents/graf-f200-calendar-test.UjB7WI/receipts-round255b`.
Для каждой успешной квитанции все source_hashes независимо сверены с canonical
рабочей копией, mismatch0. Release/Debug/full source maps равны одному
171-input frozen manifest; SDK map равен178-input manifest. Во всех четырёх
успешных квитанциях terminal=true, phase=passed, build_exit0; configure/test0
у трёх test cohorts, restore0 у SDK. Full receipt test_count50 и EXE entries50.

| Экспортированный receipt | SHA256 лично прочитанного файла |
| --- | --- |
| `graf-f200-format-round255b.json` | `589c3c8c297263ff5eb4da796a24a46cbe864ad61e2b8b5b4056bc12359f089a` |
| `graf-f200-format-round255bdebug.json` | `7b69a1ba6327a1c6f97c6eb186163959ad84c7f0697c8b16ba3a22d5815885d0` |
| `graf-f200-all-round255b.json` | `57a680e05b9006e2e664f204a57e8630498950bbd1269063ea4b155628f7a4d6` |
| `graf-f200-sdk-format-round255b.json` | `55019b7fc120871e741ae4dc72e42f252e1db8bfda73ded0d68ddeefeab96feb` |
| `graf-f200-format-round255red.json` | `f7d41ceb42c9daaf2f1dc1943baaca3d93c774321fd9ee9f002c54a8653dec95` |
| `graf-f200-format-round255.json` | `9a2fa6883f3ca762b2afa80080c7ad773305478828dcd91119f9b017c474ffb8` |

MAIN169fc2 terminal0 передан исполнителем: actual NTFS/mirror171/178 и
actual4 Release/4 Debug/50 full EXE/SDK app совпали с originals; все шесть
export SHA совпали с originals. Reviewer самостоятельно проверил экспортные
bytes/SHA, поля, source maps и согласованность EXE identities между cohorts;
**не хешировал Windows EXE/NTFS непосредственно**, не запускал VM команды.
Эта разница полномочий сохранена в окончательном допуске.

| Test EXE | Release SHA256 (совпадает focused и full) | Debug SHA256 |
| --- | --- | --- |
| V5LocalRecordingWriterTests | `084a305f440439473b188b245c1ac6246bd0b58eb9248d9589b9f9973040353b` | `82821696968ea0d8b0b90cdcae4295774148fc5a8d919b1eb218a41b5395fcc5` |
| NativeHashFailureTests | `90aedb4370074684c43b61ee2479865969644e2c6e0300c82736189c54ddffe7` | `19eda2b9af8c1c79903bdf3a68c90c391e0bbda4ecfc8b4e28d31053027a8d9e` |
| CaptureFaultStateTests | `9d061aab23e2c94dcada5868bc52345678289ba73b50e609156ac9eafeeb825e` | `d221e7f63ae86d04a6c68317e4723354cbc0c7a24e3c557fa31977c611b06cb0` |
| DesktopUploadRecoveryTests | `c1312df8b3a21c1e069432ecac37cfbeeb6a759cf5646a60abf4ff909969b31a` | `568e34ad461bb38a359f7bff664b51ec5bc1bfc7a8ffc1324839339e7fc82565` |

SDK app SHA256 `422ca203998b357c974db84be4bd36f51bdde1c581704d4cb0bb2561b246da0b`
совпадает с переданным main значением и финальной документацией. Это build
identity, не подпись/установка/запуск/аппаратная запись. AEC3 source identity
и прежнее D9025 предупреждение не превращены в новые runtime assertions.

### Принятые результаты и сохранённая неудачная история

Переданные terminal outputs: Release4/4 PASS24.38s, Debug4/4 PASS28.48s,
full Windows50/50 PASS243.68s (`22070/2e3358`), portable46/46 PASS21.58s,
focused portable3/3 PASS7.96s, SDK restore/build0. Full Owner176.78s,
Tree24.46s, Files8.25s; timeout300/j1 не увеличен, exclusions0 по переданному
исполнителем выводу и финальному validation append. Test counts/timings не
изобретены из JSON: JSON подтверждает exit/identity, timings и50/50 summary
атрибутированы main terminal. No real server/device E2E claim.

Initial RED receipt лично подтверждает configure0/build0/test8, terminal failed,
old production SHA `7cfc575282ae03714b52adc219d798121dcbf6d6c4af8a3398f7760de8c30a40`
совпадает с исходным baseline. Assertion49 подтверждена переданным main
терминалом, не полем receipt. RED test source SHA
`c618094010bdf122562c873694e0557e92f7fbe806bf01a2e3725776311c2973`
не назван исходным baseline test или нынешним GREEN255b.

Failed255 receipt лично подтверждает build1/testnull и пустые EXE hashes.
От нынешней171 source map отличается только NativeHashFailureTests.cpp
(`e220236caf0e51c53330783ddef2c0f88c44109719500789044cd306c33c09d4`).
Это ровно исторический index→audioFrame fix; не runtime успех. Stale/RED
несовпадения с GREEN expected и не блокируют совпавший frozen255b снимок.

### Окончательная scoped документация и сохранность

Лично перечитан финальный append `Окончательное выполнение255b и actual reread`
в validation: четыре receipt SHA, SDK/V5/Recovery EXE SHA и история RED/failed255
совпали с реально прочитанными экспортами. Прежний текст PENDING сохранён
исторически и явно обновлён отдельным append; чужой SOURCE GO не присвоен.
Новые full50/reread две строки F200 находятся внутри именно
`release_notes_round255_shared_package_format`, не соседнего historical entry;
лично разобран YAML и извлечено это значение. Known limitations остаются в нём.
Quickstart не изменился после промежуточного личного чтения.

| Финальный документ | SHA256 до записи этого verdict |
| --- | --- |
| `validation-2026-10-02.md` | `7f5bf81b1c9e7afcd2caf2461f9d659d558ad0d77c402ef74c9d5ea27cb0e9f0` |
| `quickstart.md` | `bfb69e14ccf1fa01cd2e6f31bb6ac3df995e25cd0fa807cdb1fdaa8b1de2abe3` |
| `changes/unreleased/F200.yaml` | `ef7ab4e5bd1a2209cedd2db03bf1ca7763e7165595ee44ffb1fe36f3370de8d7` |

Все104 прежних checklist/report SHA повторно совпали104/104; tasks SHA
не изменился,120/93/27 не переотмечены. Reviewer YAML parse и diff-check PASS.
Единственная reviewer запись — append к этому SOURCE report; code/docs/tasks,
GitHub, VM, устройства и пользовательские записи не менялись. Независимый
scoped GO допускает продолжение основной защищённой интеграции T116 по плану,
не её закрытие. H250/installed/release ограничения остаются в силе.
