# T116: независимая проверка сохранённых Owner/resume результатов

Дата: 2026-10-27. Область: сохранённые receipts, журналы и исходники
`protectedUploadFromCold` / `--protected-scheduler-resume`. Новых запусков,
доступа к guest, изменений кода, нормативных документов, чекбоксов и GitHub нет.
Этот файл — отдельный отчёт reviewer. HEAD:
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.

## Результат

В проверенной области нет подтверждённого актуального C/H дефекта зависания.
Старый Owner deadline и aligned-resume FAIL сохраняются как история своих
исходников. Их нельзя выдавать за последний результат: позже сохранены полный
Owner PASS и resume PASS. Это не закрывает T116 и не является приёмкой всего
продуктового защищённого потока или его производительности.

Свидетельства ниже прочитаны на Mac из сохранённого stage, а не получены
независимым наблюдением Windows VM. PE-хеши — данные receipts и wrappers;
исполняемые файлы в guest в этой проверке повторно не хешировались.

## Фактическая последовательность

Общий каталог: `/Users/yshishenya/Documents/graf-f200-public458.po8CtB`.
Время журналов — Turkey Standard Time, 2026-10-27.

| Stage / свидетельство | Фактический результат |
| --- | --- |
| `t116-aligned-resume.NXKcRG/resume.actual.log`, `resume.xml`, `resume.json` | 13:45–13:48; assert ожидания `cutReached`, строка 3519 сохранённого кандидата; exit 1, elapsed 177148 ms, JUnit 1 failure. Это не внешний Owner deadline. |
| Тот же stage, `success.actual.log`, `success.json` | Success PASS, elapsed 44715 ms, тот же PE и manifest. |
| `t116-inspection-phases.aWIZcf/resume.actual.log`, `resume.json` | 14:23–14:25; exit 1, `resultHeld` false. Диагностика локализует ожидание до первого wire-вызова, внутри открытия холодных readers. |
| `t116-resume-case-wait.yb1IZa/resume.actual.log`, `resume.xml`, `resume.json` | 14:29–14:32; exit 0, passed 1, elapsed 177411 ms; JUnit 1/1, failures 0, skipped 0. Оба `pass=0/1 result_flush_pending=pass` и конечный partial-ACK/retry/cold-suffix/no-resend маркер присутствуют. |
| `t116-owner-full.UjRIFg/run.json`, `owner.xml`, `owner.out` | 14:47–14:49; exit 0, passed 1, elapsed 139667 ms, owned_processes 0; JUnit 1/1, failures 0; полный Owner завершился PASS за 138.876 s. |

Привязки:

- Aligned FAIL/PASS: PE
  `a60d707ff7f226ed3463ad484ee20b167f28dd095a733d6b01eadf648533092a`,
  manifest `a40477444d885dc452e1fd674cd20c138642dc85c62922783757f1a87d44346a`.
- Поздний resume PASS: PE
  `3bb5858e04ac6c293f7fc1088aa566c57453a3bb4aa7252641da42f7a2852785`,
  manifest `d1c5ea736973c9f90a41af12ee5b59d8b67d0b9dc2bde8b4ca4f822651f72dc8`.
- Полный Owner PASS: PE
  `ea1c4e96e22da28bb2a6f306483745544439e50238bef21febdbd596b597b1eb`,
  manifest `6df03a22629ef562556b1a97c45830a04d289da2bd4e10312d79e3d864e06d4c`.

Для позднего resume и Owner проверены SHA сохранённых manifests и соответствие
хешей обоих wrappers полям receipts. Для resume также проверены все четыре
сохранённых candidate-файла против manifest. Wrapper выбирает точный CTest,
сверяет 216 исходников до/после, PE до/после и проверяет JUnit/конечный маркер.
Название `t116-partial-resume-green.EkyMJX` само по себе ничего не доказывает:
в нём найден build receipt, но не resume run receipt.

## Конкретный механизм прежнего отказа

1. После committed uploadPrepare тест вызывает `scheduled.pollUploads()` для
   adoption и выпуска настоящего executor. Затем `waitFor(cutReached)` ждёт
   всей работы до удержанного flush результата. Старый default `waitFor` —
   10 секунд, шаг опроса 5 ms. Это не таймер только HTTP и не общий CTest deadline.
2. Executor `NativeCapture::protectedUploadStep` сначала получает proof pair,
   затем выполняет `LocalRecordingPackage::inspectProtected` на том же executor
   и только после успешной проверки вызывает `uploadProtected`. В resume
   используется 14000-frame пакет, media 4480044 bytes, часть 4194304 bytes.
3. Диагностический FAIL в `t116-inspection-phases.aWIZcf` на ~10.245 s показывает
   `wire=0`, `flight=1`, `cancelled=0`, `done=0`, stage 0/1/2 достигнуты,
   stage 9 достигнут на 242665 us, stage 10 и стадии 3/4/8 ещё не достигнуты.
   По исходникам stage 9/10 окружают `openProtectedCustodyReaders`; значит,
   граница timeout находится внутри этого вызова, до возврата inspection и HTTP.
   Счётчики содержат десятки тысяч завершённых native calls. Это не доказательство
   застревания конкретного WinAPI и не доказательство, что уже началась следующая
   фаза проверки hashes/AAC. Нулевые error-поля до выхода стадии также не доказывают
   успешное завершение проверки.
4. Между `t116-inspection-phases.aWIZcf` и `t116-resume-case-wait.yb1IZa` сравнение
   четырёх candidates показывает единственное изменение: ожидание `resultHeld`
   стало `partialResume ? 30 : 10` секунд с поясняющим комментарием. Header,
   package implementation и CMake побайтово одинаковы. CTest timeout остался 240 s.
   Поздний PASS прошёл обе реальные точки flush, durable retry generation 5,
   cold resume с suffix 4194304 и uploaded generation 7 без повторной отправки.

Таким образом, подтверждён прежний слишком короткий функциональный test wait;
его исправление имеет сохранённый PASS. Блокировка на ожидании удержанного
результата не подтверждена. Точная стоимость внутренностей открытия readers
не измерена этим PASS; утверждать более точную причину задержки нельзя.

## Соответствие текущим исходникам и границы переноса

Текущие 220 файлов совпали со всеми 220 записями
`settings-chain-li1qcg1c/startup-quit-production-source.json`, SHA
`ff9a8e158a8a417a65a5c9292b8be05d707b7145a073e4a565740edd761a72ce`.

- Current `NativeCapture.h` и candidate позднего resume PASS совпадают:
  `95b0c03cc98cfa2e4dd138de5f4b96a99bdaa23654e87ef5c19e92c849d70e37`.
- Current `LocalRecordingPackage.cpp` и candidate того PASS совпадают:
  `db1019752c28960639a49c99feaf52452ea45900277d1352ac623e13fa2b9b04`.
- Current `NativeCaptureStorageIntegrationTests.cpp`:
  `54ffe2c826366d7b4775fc2bcec92fc517d271064c0f5595d2edd431746c12b9`;
  кандидат PASS: `3a3820d4157a894eae58dabe427ab75a0d8772e754107f278a546afbeb6f9909`.
  Полный diff прочитан: добавлен отдельный late-logout сценарий/ветки и получение
  committedEpoch; для resume по-прежнему lateLogout=false, ожидание 30 s сохранено.

Полные исторические manifests не равны current: aligned имеет 9 несовпадений
из 216, поздний resume — 7, Owner full — 6. Для позднего resume отличаются
CMakeLists, AppMain, этот integration test, NativeSettingsBridgeTests,
ProtectedPackedCustodyOwnerTests, RecordingIndicatorTests и prepare-appmain-problem-ui.
Для Owner full совпадают актуальные NativeCapture, LocalRecordingPackage и сам
ProtectedPackedCustodyOwnerTests, но это всё равно не свежий PASS всего current220.
Startup-fix AppMain не участвовал в перечисленных старых запусках.

## Минимальный следующий шаг

Новый запуск ради выяснения этого старого FAIL не нужен: сначала учитывать уже
сохранённый более поздний PASS и сохранять прежние FAIL как историю их версий.
Нового production diagnostic API или расширения timeout сейчас не требуется.

Если отдельная новая цель действительно потребует запуска current resume,
сначала привязать его к новой сборке/manifest; при отказе снять уже существующий
`PROTECTED_SCHEDULER_WAIT` и stage/native counters в точке `resultHeld == false`
(`NativeCaptureStorageIntegrationTests.cpp`, текущие строки 3579–3607).
Интерпретировать по границам: 0→1 — proof handoff; 9→10 — открытие readers;
11→12 — validateProtectedContent; 4→8 — transport до первого send; 5/6/7 —
завершение transport и освобождение proof; далее — result flush/adoption.
Сравнение двух временных snapshots счётчиков, если новое зависание реально
возникнет, отделит продолжающуюся работу от остановки прогресса; существующий
однократный snapshot этого не делает. Не записывать paths, токены, содержимое,
идентификаторы владельцев и прочие пользовательские данные.

Никаких новых runtime, performance, hardware, installed-app или T116 closeout
утверждений эта проверка не добавляет. Pending HTTPS/cert prompt не затронут.
