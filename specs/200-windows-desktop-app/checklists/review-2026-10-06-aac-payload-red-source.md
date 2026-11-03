# Round257c — SOURCE review только изолированного AAC payload RED

Дата: 2026-10-06. Reviewer проверяет исходник диагностики, не production fix.
Canonical: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`;
ветка `codex/200-windows-followup`;
HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`, dirty preserve.

## Решение и граница

**APPROVED — SOURCE изолированного диагностического контрпримера Round257c.**
Блокирующих дефектов в построении этого контрпримера не найдено. Это не GREEN,
не разрешение менять production, не одобрение protected inspector и не закрытие
T116. `REQ257-B1` и общий NO-GO остаются без изменений.

Reviewer лично прочитал весь текущий test и соответствующий production helper,
сверил порядок проверок и SHA. Лично прочитаны/разобраны два JSON exports и
сырой CTest log, проверены их hashes и все 171 source-map записи относительно
canonical worktree. VM, сборки, тесты, устройства и GitHub reviewer не запускал.
Проверка сохранённого receipt не выдаётся за собственное выполнение в Windows.
Единственная запись reviewer в данном задании — настоящий новый отчёт;
старый gate и остальные отчёты не меняются.

## Замороженный исходник

| Объект | SHA-256 | Как подтверждён |
| --- | --- | --- |
| `apps/windows/Tests/GrafWindowsCoreTests/NativeHashFailureTests.cpp` | `a2d6d9a8e1dd0ea75832d987502b4cfd6a41cfd0414e6506c60ea933cc8f3f76` | Лично прочитан и хеширован; это Round257c, не b |
| `apps/windows/RecApp/Recording/LocalRecordingPackage.cpp` | `38b709c9a184ac586b1112cf934e4bfbada400815202eaad34aa463fda13b859` | Лично прочитан/хеширован; production не изменён |
| Предыдущий `review-2026-10-06-protected-inspector-gate.md` | `6490e3f48594effb0ccf9a2886b296ec9ffbfb6119691462b1eb16d838320452` | Хеширован, неизменен |
| Source171 manifest Round257c | `e4de5f59413b5c11f1172e10d1e2636d1420025d9c594bd26dbf6f52bd47fd2c` | Лично прочитан, parsed и хеширован; 171/171 canonical MATCH |

Базовая версия теста до AAC RED имела SHA
`65035b070a2ce26e10a3dca51d5af4b24c3c59d9e7d3da131b435bf96fdc4fc4`.
Проверка в памяти: удалить из текущего текста только новый AAC блок и шесть
новых includes (`algorithm`, `iterator`, `iostream`, `mfapi.h`, `mfidl.h`,
`mfreadwrite.h`), вернуть прежний cleanup — получается ровно этот SHA.
Файлы при такой сверке не создавались и не изменялись. Следовательно, прежние
CNG/positive/upload assertions действительно сохранены, а не заменены новым RED.

## Лично проверенная причинная цепочка в исходнике

1. Строки 272–304: реальный `V5LocalRecordingWriter` пишет 100 canonical 10ms
   блоков с синтетическим сигналом. Сначала проверяются normal package,
   положительный upload/mock baseline с `creates == 3`, hash-fault отказ с
   `sends == 0`, затем отсутствие повреждения последующей CNG работы.
   Новый блок расположен после них. `NDEBUG` снимается перед `<cassert>`,
   поэтому checks не исчезают в Release.
2. Строки 310–344: отдельный native SourceReader декодирует оригинал в PCM
   через ReadSample до EOS; успех требует непустого вывода и не более 52 800
   отсчитанных PCM кадров для этого 1s примера. Нет подставного encoder или
   stub вместо настоящего native decoder.
3. Строки 355–377: небольшой обход top-level MP4 boxes используется **только
   в тесте**. Проверяются границы 8/16B заголовков, extended size и size0 до
   конца файла; продвижение не допускает нулевого размера. В каждом найденном
   `mdat` только диапазон после заголовка заполняется `0xff`, без вставки,
   удаления, изменения box lengths, `moov`/таблиц или длительности. Нового
   production container parser нет.
4. Строки 350–354, 377–381: найден единственный исходный playback digest в
   manifest; он заменён новым digest того же размера. Audio length остаётся
   прежним; metadata fields кроме playback SHA не меняются. После записи
   hash faults отключены. Это не тест отказа из-за устаревшего SHA/размера.
5. Строки 382–394: тот же native контроль проверяет повреждённый файл.
   Только после него выполняются explicit-root inspect, default-root inspect
   и upload с существующим injected `UploadSend`, возвращающим synthetic 503.
   Счётчик сбрасывается перед upload. Печать до падающего assert содержит
   только счётчики/признаки — не пути, секреты или содержимое.
6. Строки 395–398: ожидается malformed/unavailable/invalidPackage/no-send.
   Текущий production helper читает native AAC/rate/channels и container
   duration, но не payload PCM. Поэтому полученный false-valid имеет прямую
   причинную связь с отсутствием проверки декодированных данных.

### Порядок освобождения Media Foundation

`IMFSample` объявлен внутри каждой итерации: уничтожается при выходе/`break`.
`IMFSourceReader` и `IMFMediaType` живут во внутреннем scope 316–338, который
заканчивается до `MFShutdown` на 339 и `CoUninitialize` на 340. Ни reader,
ни sample не удерживаются после shutdown. Настройка COM/MF проверяется assert;
ошибка setup не маскируется как успешный контрпример payload.

## Лично проверенные exports и сырой журнал — без выполнения reviewer в VM

Все три файла лично прочитаны и хешированы из
`/Users/yshishenya/Documents/graf-f200-calendar-test.UjB7WI/`:

| Файл | SHA-256 |
| --- | --- |
| `graf-f200-aac-round257c-red.json` | `5f03e09e55007412e204344bdc3f018ed0f399b6ecc9b57cb359ea389e37256d` |
| `source-aac-round257c-red.json` | `e4de5f59413b5c11f1172e10d1e2636d1420025d9c594bd26dbf6f52bd47fd2c` |
| `graf-f200-aac-round257c-red-test.log` | `a3293610fb8918d57f30c27e9c8000111923c8ae9f567c8027d2a475a7340b02` |

JSON receipt разобран с удалением UTF-8 BOM **только в памяти** для чтения
внешнего диагностического JSON. Export не переписывался/не нормализовался;
его SHA выше рассчитан по исходным bytes с BOM. Это не protected payload parser
и не разрешение BOM в product codec: его прежний строгий отказ сохраняется.
Лично сверенные поля: schema1,
mode `aac-payload-red`, phase `failed`, terminal=true, configure_exit0,
build_exit0, test_exit8, source_count171. `source_hashes` содержит 171 запись,
полностью равную отдельной source map; все её пути нормализованы из Windows
разделителей и сопоставлены с `apps/windows/` canonical. Итог: **171/171 MATCH,
missing0, mismatch0**, включая test, неизменный production helper, writer,
transport и CMakeLists. Это сверка hashes, не новая проверка всех 171 исходников.

Receipt содержит EXE hash `NativeHashFailureTests`:
`dd3eb9010153792a2740766ae104704d60195687b0125019cafd146d98740d47`.
Значение совпадает с сообщённым main actual NTFS reread; reviewer лично
проверил поле экспортированного JSON, но не читал EXE на NTFS и не выполнял его.

Raw log содержит один test section NativeHashFailureTests, команду
`C:/Temp/graf-f200-calendar-native-build-UjB7WI/Release/NativeHashFailureTests.exe`,
build directory того же имени, строку счётчиков ниже и assert395 из
`C:/Temp/graf-f200-calendar-source-UjB7WI/Tests/GrafWindowsCoreTests/NativeHashFailureTests.cpp`.
Он явно фиксирует `Test Failed` и **2.19 sec**. `47/50` — индекс этого теста
в зарегистрированном наборе, не свидетельство запуска или PASS всех 50 тестов.
Общие 2.20s сообщены main, но отсутствуют в этих трёх exports; independently
verified total-time claim не выдан. Raw build/configure output здесь отсутствует:
их exit0 подтверждён полями receipt, не отдельным build-log review.

Round257c actual operation `57842/8c690e` сообщена main; запуск reviewer не
выполнял. Строка метаданных лично прочитана в замороженном raw log:

```text
original_frames=48128
corrupt_decode_complete=1 corrupt_frames=0
explicit_root_normal=1 explicit_root_playback=1
default_root_normal=1 invalid_package=0 synthetic_sends=1
```

Эта строка и проверенный исходник доказывают для конкретного примера:
оригинал выдаёт непустой PCM, после порчи native reader
**доходит до EOS с нулём PCM-кадров**, но оба inspect всё ещё считают пакет normal,
явный root даёт playback, а mock upload допускает одну отправку вместо
invalidPackage. **Это не native HRESULT decoder error. EOS сам по себе
недостаточен; нужны фактические непустые данные и их длительность.**

`synthetic_sends=1` — вызов injected callback, не реальный HTTP/сервер/provider.
Достижение assert395 означает, что предшествующие CNG/positive/control и
вычисления root/default/mockupload выполнены. Поздние asserts396–398 и cleanup
не достигнуты, поэтому нельзя назвать их PASS. Нельзя объявлять GREEN или
«50/50» для набора, в котором ожидаемо падает этот RED.

Round257b (test SHA `14f1e15b04cca4926ee3a7b22af25ffeb24ce9a966d0acd790877dc01a199520`)
остановился на assert384 до поздних default-root/upload assertions. Такие
проверки не приписываются b; они вынесены перед failure только в c.
Первый RED с test SHA `f829083dab24e046659b57d0dd18719032ef7fadee3d464886c7b9158173c6a6`
не используется как свидетельство strengthened native-control/c branches.
EXE первого запуска был перезаписан до независимого reread; его проверенный
фактический hash reviewer не заявляет. Проверка export c завершена; прежняя
отметка об отсутствовавшем пути снята после получения точного каталога.
Actual NTFS/mirror/source/EXE reread `63481/c8f109` остаётся работой main;
reviewer не выдаёт собственную файловую сверку Mac exports за выполнение в VM.

## Ограничения диагноза, не разрешение production

- `decodeSynthetic` — контроль конкретного сгенерированного файла. Не проверяет
  полностью actual PCM type/rate/channels, timestamp/duration, AAC-LC/implicit
  SBR или отсутствие extra streams. Его нельзя переносить в production как
  готовый validator. Счётчик здесь рассчитывается `bytes / 2` для известного
  mono PCM fixture; это не независимая проверка всех output media attributes.
- Предел 52 800 ограничивает обработанный вывод данного примера, но не время
  блокирующего ReadSample, native allocations или concurrent jobs. Настоящие
  owned-input/cancel/job/currentness условия по `REQ257-B1` остаются обязательными.
- Нулевой вывод при EOS выявлен этим примером; не обещается обнаружение любого
  возможного изменения AAC. Не выбирается новая codec policy или новый порог.
- Здесь только synthetic files в отдельной test temp directory, нет capture
  устройств, пользовательского профиля, настоящего network или новых полномочий.
  Отказ assert оставляет test cleanup недостигнутым; это не проверка lifecycle
  приложения и не разрешение удалять другие данные.

Финальное решение: **APPROVED diagnostic SOURCE + exported RED evidence review**
для точного Round257c test SHA выше. Export/schema/source maps/canonical hashes,
raw command/counts/failure line сверены лично; расхождений в этих проверках нет.
Это конечная проверка конкретного контрпримера, а не общий native/SDK/Debug/full
PASS или whole-pipeline proof. Production GO и старый gate не меняются;
`REQ257-B1` остаётся NO-GO до минимальной настоящей input/job/cancel границы.
