# Независимый ограниченный обзор T116: native hash failures

Дата: 2026-10-02. **Approved — только текущие исходники bounded-hash и детерминированных регрессий.** Новых блокирующих замечаний P0/P1/P2 к просмотренной дельте не найдено. Нативная сборка и исполнение тестов пока не подтверждены; это не закрытие runtime gate, полного T116 или Windows release.

## Область и правила

Рабочая копия: `/Users/yshishenya/.codex/worktrees/200-windows-followup/crisp`; ветка `codex/200-windows-followup`; HEAD `99b00a579c24b50e320465b69d9a296038bc544d`. Обзор относится к незакоммиченным bytes поверх HEAD, а не только к содержимому коммита. Активная feature подтверждена `.specify/feature.json`.

Полностью прочитаны `code-reviewer` и `ponytail-review`, root `AGENTS.md`, guidance index; применены risk/worktree/product/evidence правила и относящиеся к этому срезу положения конституции. Прочитан предшествующий `review-2026-10-02-bounded-hash.md`, включая свежий раздел после исправлений; его исторические findings не перенесены на новые bytes автоматически. Проверены текущие `Sha256.cpp/h`, CMake, оба SHA-теста, дельта transport и необходимые caller/build boundaries. Остальные Windows release-пути не проверялись.

Lane: независимая read-only проверка кода активного high-risk T116; единственная документная запись — этот отчёт. Production/spec/plan/tasks/contracts и отметки чеклистов не менялись. Сборки, C++ тесты, CLI VM, устройства, сеть продукта, коммиты и GitHub действия не выполнялись.

## Причинное устранение BH01–BH03

| Замечание прежнего обзора | Проверенный источник | Вывод по текущим исходникам |
| --- | --- | --- |
| BH01, P1: CNG exception через reminder destructor | `Sha256.cpp:159–162`; `MeetingReminderPresenter.cpp:56,64–70`; `MeetingReminderModel.cpp:38,175,194,285–290` | Memory `sha256()` всегда создаёт `PortableHash`, без CNG. Отказ native provider больше не может вызвать прежнюю цепочку terminate. Общий primitive исправляет все эти callers; новые ловушки в presenter не нужны. |
| BH02, P1: CNG exception при deletion operation ID | `Sha256.cpp:159–162`; `DesktopApiClient.cpp:845–857` | Operation ID использует тот же независимый memory primitive. Прежний native trigger исключения устранён без изменения identity/UUID semantics или deletion flow. |
| BH03, P2: manifest no-hash допускает отправку | `DesktopHttpTransport.cpp:177–182,590–591,896–900` | Manifest digest проверяется `isSha256()` до возврата tracks и любого UploadSend. Проверка ожидаемого track digest исключает empty == empty. При no-hash возвращается `invalidPackage`. |

Memory API не объявляется безусловно `noexcept`: неподдерживаемая длина даёт `length_error`, выделение результирующей строки может отказать. Это не прежняя CNG-зависимость ограниченных identity inputs. Native stream/file не переходят на portable после ошибки: маршрут выбирается заранее по API (`Sha256.cpp:165–193`).

## Достаточность нового теста по исходникам

- `NativeHashFailureTests.cpp:19–37,45–53`: SDK headers включены до локальных macros. Четыре wrappers на обычных стадиях делегируют настоящим BCrypt; выбранная стадия возвращает отрицательный NTSTATUS. Включается настоящий `Sha256.cpp`, затем macros снимаются. Нет production knobs, DLL hooks, системной настройки provider или нового интерфейса внедрения отказов.
- `NativeHashFailureTests.cpp:68–85`: normal native stream проверяется фиксированным abc digest и счётчиками; regular file сравнивается с memory digest. Open/Create/HashData/Finish failures проверяются для stream и file. Второй HashData после успешного первого 64 KiB не должен вернуть prefix digest. Memory abc остаётся корректным при включённом отказе и не увеличивает Open/HashData counters; проверка повторяется после native failure. Это непосредственно проверяет удалённый общий trigger BH01/02, а не имитацию reminder/deletion.
- `NativeHashFailureTests.cpp:88–114`: fixture создаёт настоящий `V5LocalRecordingWriter` без faults; настоящий `LocalRecordingPackage::inspect` обязан вернуть `valid`. Encoder выдаёт синтетические playback bytes: тест не доказывает AAC playback и не заявляет его. `finalize()` по умолчанию использует `interruption` (`V5LocalRecordingWriter.h:70–72`), поэтому один frame не маскируется normal-short discard. Owner UUID, workspace, session и confirmed identity согласованы; существующие проверки transport их допускают (`DesktopHttpTransport.cpp:688–701,849–857`). Baseline требует `retryableFailure`, ровно один Send и три Open, поэтому auth/precondition rejection не может дать ложный успех.
- `NativeHashFailureTests.cpp:116–119`: после сброса counters отказывает только третий Open. Первые два hashes — media/playback в настоящем `LocalRecordingPackage.cpp:157–159`; третий — manifest в transport. Требуются одновременно `invalidPackage`, `opens == 3`, `sends == 0`. До нового manifest guard прежний transport дошёл бы до Send; это причинная регрессия BH03. Контрфактический запуск прежнего transport не выполнялся. После выключения faults проверяется следующая успешная операция (`:120–121`).
- `CMakeLists.txt:12–16,54–84`: обычный SHA вынесен из common в отдельный object; все обычные тесты получают его. Windows-only fault executable получает настоящий common production-код, но не второй обычный SHA object. Нет duplicate SHA symbols или подмены transport/package/writer моделями. `/W4 /WX` сохранены, `bcrypt` присутствует. `GrafWindowsApp.vcxproj:92,95,109–110,146` по-прежнему подключает обычные production sources; fault test не добавлен в приложение. Отдельный Core VS project не запускает новый executable: новый regression target зарегистрирован в CMake/CTest.

Это достаточная адресная конструкция регрессий для этого code-review среза. Фактический native compile/run PASS всех assertions ещё нужен от main на этих же bytes; наличие теста не равно выполнению gate.

## Безопасность и сложность

`Sha256.cpp:52–83,87–118`: portable compressor сохраняет SHA round/state, big-endian length/output и padding; input не копируется целиком. Размер block 64 bytes, working arrays фиксированы, ёмкость bit length проверяется до update. Актуальное исправление обоих `std::fill` на `std::uint8_t{0}` присутствует на строках 72 и 76; `/WX` не ослаблен.

`Sha256.cpp:124–148,172–184`: input buffer 64 KiB, каждый native update не больше 64 KiB, digest 32 bytes; narrowing в ULONG ограничен. RAII освобождает реально созданные hash/provider handles, включая Create failure. При badbit, non-EOF failure или недопустимом gcount digest не выдаётся; normal EOF допустим и с exception mask. После native update failure внешний stream helper возвращает no-hash без Finish/fallback. Cleanup подтверждён чтением кода, отдельные cleanup counters в тесте не заявляются.

`Sha256Tests.cpp:38–84` сохраняет empty/abc/million-a, padding/chunk boundaries, NUL, cursor, initial failed state, throwing EOF, read failure после первого chunk и generated 64 MiB + 5 с ограниченными чтениями. Это дополняет native status failures, не заменяет их. `sha256File()` остаётся path-based; same-handle protected logical IO ещё не реализован этим срезом. Отдельный same-handle executable hash не удаляется ради формального reuse.

Ponytail-review: отдельный test TU и SHA object нужны для реального production integration без production injection. Новых dependencies, общего fault framework или speculative abstraction нет. **Lean already. `net: 0 lines possible.`** Этот вывод относится к сложности, не к runtime/release готовности.

## Проверки, ограничения и статус требований

Независимо выполнены только чтение кода, проверка branch/HEAD, SHA-256 pins и `git diff --check -- apps/windows` — PASS. По сообщению main свежая native сборка выявила `/WX C4244` в padding; проверяемые bytes уже содержат два typed-zero исправления. Native baseline/test ещё running; свежие результаты не предоставлены. Старые 33/33/Core PASS из предыдущего отчёта не принимаются как подтверждение новой дельты. Сборки и VM reviewer не дублировал.

Accepted T115 requirements остаются **112/112, без изменений**: это подтверждённый отдельными requirements reviews допуск качества требований, не 112 runtime tests. Текущий accepted contract hash совпадает с прежним `630b85b2a077788a90d23d5763561dce320e317aeddabe8ae5fe8810853bdba0`. Повторная приёмка всего contract не выполнялась, markers не менялись. **Полный T116 не завершён**: protected logical IO, encryption, recovery/migration/playback и дальнейшие T117/T118 gates не принимаются этим обзором. T119/clock и whole-Windows release не являются findings этого среза.

При любом новом compilefix теста/source нужны свежие pins и повторное чтение его дельты. Результат native build/run main должен быть привязан к HEAD плюс незакоммиченным pins, включая оба untracked tests.

## Exact pins

SHA-256 `git diff --binary HEAD -- apps/windows`: `3f835e25a755d668e8df0953c18d8ca08740675b2cba619b4c8e15e9749348c4`.

SHA-256 scoped tracked diff только CMake/Sha256.cpp/Sha256.h/DesktopHttpTransport.cpp: `09fa6e8b05610f9c9d3aa92e79c542889d74a54799e7da396464aed74bdd50e2`.

Untracked tests **не входят** ни в один tracked diff; их bytes зафиксированы отдельно. Пути ниже относительно canonical worktree. Pins caller-файлов относятся к использованным границам, не означают полный обзор этих модулей.

| Tracked исходник / использованная граница | SHA-256 текущих bytes |
| --- | --- |
| `apps/windows/CMakeLists.txt` | `ab90c5d1ec00302a17c00485c9347933f527903ca80740e2f71501fc65125238` |
| `apps/windows/RecApp/Storage/Sha256.cpp` | `cfad493c54a1b6f0db19bdc0aa80858e18e8396c8605b58b2a91ebea33e01ca2` |
| `apps/windows/RecApp/Storage/Sha256.h` | `e51b352aa346036708ad30867fed412b67000434b87d88aeb02c45549c43cc60` |
| `apps/windows/RecApp/Upload/DesktopHttpTransport.cpp` | `34bfb5d5359c22c5de26bd790227414974d4804abdd6588e8e63734022e9fce1` |
| `apps/windows/RecApp/Recording/LocalRecordingPackage.cpp` | `7cfc575282ae03714b52adc219d798121dcbf6d6c4af8a3398f7760de8c30a40` |
| `apps/windows/RecApp/Recording/LocalRecordingPackage.h` | `bd54424e3e9b826c3233d5a1158247ecec0ef5aff9cef34887097192c87dc698` |
| `apps/windows/RecApp/Recording/V5LocalRecordingWriter.cpp` | `b890339cfc0b21d1ef3d6c2840e01e2eb5ecabbdf5444593682279f780c6c453` |
| `apps/windows/RecApp/Recording/V5LocalRecordingWriter.h` | `2ba317fc5ae6bb73d3ef746c34e69d70a73a41cf725379b5dd0c0b5e8e0fae56` |
| `apps/windows/RecApp/Shell/MeetingReminderModel.cpp` | `ad053893499165c639ce41c4a23115ff17a5bb3d775ec568ae311e8f8d4529b7` |
| `apps/windows/RecApp/Shell/MeetingReminderPresenter.cpp` | `dd0bc9dee51329582e227fb164000cf6d4ba7188abd985985998f8dff5a33d56` |
| `apps/windows/RecApp/Upload/DesktopApiClient.cpp` | `84527d7b7457555aac578b7399227a7a0d8b3db589ebcf3e9e78455e329be900` |
| `apps/windows/RecApp/MeetingDetection/WindowsTargetDetector.cpp` | `424eb77232fae271564ae92d7a77918b45fedf8915e8543e8bfc749fa893f860` |
| `apps/windows/RecApp/GrafWindowsApp.vcxproj` | `6f0968254001ddeccea8299094d6b1ce8ebacd26174715565d93cf2daf2ac3db` |
| `apps/windows/Tests/GrafWindowsCoreTests/ContractFixtures.cpp` | `20883ed7b2252084853e87e24c23d39660a050ce006bd7d114ca03357d1f1e55` |
| `apps/windows/Tests/GrafWindowsCoreTests/GrafWindowsCoreTests.vcxproj` | `c53d070bbb0bae3f4262a875e593a56c3ff28847c5dec19e176d87d3e20d5df4` |

| Новый untracked тест | SHA-256 текущих bytes |
| --- | --- |
| `apps/windows/Tests/GrafWindowsCoreTests/NativeHashFailureTests.cpp` | `a6b54f701ca1927f941a8af914bb88395e8813e4d10d3bf512e47bf4e4db08e4` |
| `apps/windows/Tests/GrafWindowsCoreTests/Sha256Tests.cpp` | `70bf9177f14bf328299ca44ce1d0de2c2853124b228e9f6515744ca2813cebba` |

Accepted untracked contract `specs/200-windows-desktop-app/contracts/windows-protected-local-custody.md`: `630b85b2a077788a90d23d5763561dce320e317aeddabe8ae5fe8810853bdba0`.

Единственная запись reviewer: `specs/200-windows-desktop-app/checklists/review-2026-10-02-native-hash-faults.md` через `apply_patch`. Прежний отчёт и чужие изменения сохранены.
