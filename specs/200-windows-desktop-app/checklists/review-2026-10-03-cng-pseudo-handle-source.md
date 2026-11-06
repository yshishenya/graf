# Независимая проверка исходного кода: T116 / CNG SHA-256 pseudo-handle

2026-10-03. **APPROVED — только новая дельта трёх файлов. CRITICAL=0, HIGH=0, блокеров=0.** Это допуск по исходному коду, не подтверждение ускорения, установки приложения или полной приёмки T116/F200.

## Область и закреплённые bytes

Worktree: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`; HEAD: `99b00a579c24b50e320465b69d9a296038bc544d`.

Основа сравнения — pins и описание состояния до изменения из `review-2026-10-03-cng-pseudo-handle-gate.md`, SHA-256 `eefa1e86efa7295dab227d9442e3914174efafc585496d78990dd4c11a4b8b7d`. Git HEAD не подменяет эту основу, особенно для новых файлов. Остальной dirty diff не проверяется и не принимается этим отчётом.

Пути в таблице относительно worktree:

| Файл | SHA-256 до изменения, из gate | Проверенный текущий SHA-256 |
| --- | --- | --- |
| `apps/windows/RecApp/Storage/Sha256.cpp` | `cfad493c54a1b6f0db19bdc0aa80858e18e8396c8605b58b2a91ebea33e01ca2` | `af51b5cef94a0855773c1310b05bc7ef1d13a65939d2f8bc4b960ff403f0a4d2` |
| `apps/windows/Tests/GrafWindowsCoreTests/NativeHashFailureTests.cpp` | `813bc9c32a14a1189a67c61593545ca6094c1c02e477fa69dc3c5fff7f46efb0` | `d0d33db879531c2ad5debc7facad20f13b13d3e625d510415d2d37f58fc42414` |
| `apps/windows/Tests/GrafWindowsCoreTests/ProtectedCustodyFilesTests.cpp` | `7dc2b317729df8dc5410ee9c3e37dfebf543385980dd7c984c2a63626abd270c` | `a8e3aa8d60410143624e0b81d53c70056e227f8d5879f5600e669bab6005ce72` |

Обратное преобразование только конструктора/деструктора/поля `Sha256.cpp` в памяти воспроизводит точный gate SHA-256. Аналогично точный gate SHA-256 `ProtectedCustodyFilesTests.cpp` воспроизводится обратной заменой обёртки, счётчика, названия отказа и диагностического поля. Для `NativeHashFailureTests.cpp` рассмотрены новые проверки против закреплённого описания прежних Open/Create/Update/Finish тестов и требований gate; реконструкция старых bytes не заявляется.

При сверке 32 pins gate отличаются только эти три исходных файла; остальные 29 совпадают. Это проверка неизменности, не повторный аудит требований. В частности, неизменны constitution `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859`, spec `d778aa44725911288331beeddc5a2293333bf2fb39ab93e2087a471cdb4f1c0f`, plan `34e64befcd775c85ee524a8d0e097d7d08805545cec92966bfdbf98d446f71cc`, tasks `76c91845c3ce5da964351cca95b027562190bbc0fcb9f76b7159d0d021261287`, protected-custody contract `630b85b2a077788a90d23d5763561dce320e317aeddabe8ae5fe8810853bdba0`. Результат предыдущего gate — 112 checked / 0 unchecked — не изменяется этим отчётом. GitHub повторно не читался; статус T116/#7444 не переоценивается.

## Проверка новой дельты

- **Production, `Sha256.cpp:125–150`.** Конструктор вызывает `BCryptCreateHash(BCRYPT_SHA256_ALG_HANDLE, &hash_, nullptr, 0, nullptr, 0, 0)`; удалены Open, Close и поле `algorithm_`. Остаются только локальный `hash_` и `ready_`, уничтожение созданного hash и запрещённое копирование. `sha256Stream` создаёт собственный объект для каждого digest; постоянного, глобального, потокового или reusable cache нет. Удаление алгоритма из владения не удаляет владение hash. Net production: −3 строки.
- **Ошибки и границы неизменны.** Create/Update/Finish проверяют NTSTATUS; при отказе возвращается пустой результат, без portable fallback. Portable `sha256(std::string_view)` для identity, потоковые 64 KiB chunks, EOF/read-error поведение и file helper побайтно неизменны относительно gate. Block verification, ACK, index, encryption, file policy, quota и routes не менялись.
- **Реальные вызовы и flags, `NativeHashFailureTests.cpp:23–64`.** `testCreate` проверяет точный SHA-256 pseudo-handle, null/zero object/secret параметры и flags=0, затем вызывает настоящий CNG Create. Update/Finish тоже делегируют реальные функции. Обёртки Open/Close/SetProperty/Destroy ограничены включением `Sha256.cpp`, затем сняты; они не накладывают SHA-only запреты на AES или другие компоненты. Накопительные счётчики Open/Close/SetProperty проверяются на ноль перед сбросами и в конце. Прежний Open fault удалён, Create fault получил ordinal.
- **Свежие объекты, `NativeHashFailureTests.cpp:80–119`.** Проверяются Create/Finish/Destroy каждого digest, пустой поток, граница 64 KiB и следующий байт, совпадение с portable digest. Вложенный поток перекрывает время жизни внешнего объекта и использует другой payload; callback извлекается через `std::exchange` до вызова, исключая повторный вход в тот же callback. Это проверяет независимость состояний без ошибочного требования уникального численного handle после его освобождения. Create failure не допускает Update/Finish; Update/Finish failures сохраняют уничтожение hash и независимую identity.
- **Manifest и отсутствие HTTP, `NativeHashFailureTests.cpp:165–175`.** Успешная контрольная подготовка требует три Create/Destroy до HTTP. Create ordinal=3 даёт `invalidPackage`, три попытки Create, два Destroy и `sends==0`; следующая здоровая операция не отравлена предыдущим отказом. Существующие codec Update/Finish faults и второй Update сохранены.
- **Файловые отказы, `ProtectedCustodyFilesTests.cpp:113–124,1233–1247`.** Обёртка теперь перехватывает используемый Create и проверяет pseudo-handle. Allocation hook остаётся перед настоящим Create; ordinal 1–4, `hashFailed`/`ioFailed`/`allocationFailed`, native read error и sticky `writerFailed` не ослаблены. Текущий механизм `fileFault`, остальные I/O hooks и file-open счётчик сохранены. `hashOpen`→`hashCreate`, `hashes`→`hashCreates`; диагностическое поле прозрачно переименовано `cumulative_native_hash_opens`→`cumulative_native_hash_creates`, без заявления измеренного ускорения.

Primary API guidance проверена: [BCryptCreateHash](https://learn.microsoft.com/en-us/windows/win32/api/bcrypt/nf-bcrypt-bcryptcreatehash) разрешает algorithm pseudo-handle и null/zero object buffer с освобождением при Destroy; [CNG Algorithm Pseudo-handles](https://learn.microsoft.com/en-us/windows/win32/seccng/cng-algorithm-pseudo-handles) задаёт Windows 10+ и SHA-256 handle, запрещая изменение его свойств. Уже принятая в gate граница Windows user-mode сохраняется; SetProperty, kernel-mode и IRQL-ветвление не добавлены.

## Минимальность: ponytail-review

Применены `code-reviewer` и явно запрошенный `ponytail-review`. Новых production-абстракций, зависимостей, резервного пути или cache нет. Обёртки и дополнительные счётчики нужны для утверждений о реальном API, fresh lifetime и отказах; callback нужен для перекрывающихся потоков. Их удаление ослабило бы заданные проверки. За пределами этой дельты предложения сокращений не делаются.

**Lean already. Ship.** Здесь это только вывод о минимальности исходного изменения, не разрешение выпуска. `net: -0 lines possible.`

## Свидетельства исполнения и граница решения

Reviewer не выполнял сборки, тесты, VM/runtime, probe или работу с микрофоном. Ниже — сведения владельца, не независимо воспроизведённые результаты:

- RED до production edit: Windows build exit 0, test exit 8, `algorithm == pseudo`, line 26, session 8374.
- GREEN: focused native 2/2 PASS, 13.65 s (8513); full native 36/36 PASS, 71.40 s (22066); host 35/35 PASS, 33.03 s (95673); VS build exit 0 (95469), Core exit 0 (80586).
- Собранный, **не установленный** бинарь: SHA-256 `e99c6b2b5506b21a717bebda64aaf4a060bb6493e1dadc3deddb5d7995b7b9c5`. Эти сведения не расширяют source verdict. Незавершённый performance 64 MiB не оценивался; ускорение не заявляется.

**Итог: блокеров по новой pseudo-handle дельте нет.** Одобрены только перечисленные exact source bytes. Полная T116/F200 и runtime/performance приёмка этим решением не закрываются. Единственная запись reviewer — этот новый отчёт; код, нормы, существующие отчёты/чекбоксы, marker, Git/GitHub и появившийся у другого исполнителя документ 214 не изменялись.
