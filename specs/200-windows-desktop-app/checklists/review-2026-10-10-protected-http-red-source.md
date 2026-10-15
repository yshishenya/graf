# T116 — scoped review исходника HTTP RED и Debug idle baseline

SCOPED SOURCE-REVIEW GO — C0/H0/M0/L0 в перечисленных ниже границах.
Это принятие конструкции теста и его поправки, не compilation/runtime/full/
installed/release GO и не закрытие T116/#7444 или иных задач.

## Точный снимок

Canonical: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
HEAD: `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; оценены dirty bytes.
Файл: `apps/windows/Tests/GrafWindowsContractTests/NativeCaptureStorageIntegrationTests.cpp`.
SHA-256: `540ac58aa976648694f830b4a30643c72a2b09016e6eeac0ab792b3303229095`.
Применён code-reviewer; только чтение, кроме создания этого отчёта.

## Принятые исправления body/JSON P2

- Строки 720–750: копия настоящего UploadRequest сохраняется за пределами
  transport return; protectedBody связан с bodyView. После возврата проверяются
  адрес, длина и SHA; reset копии требует weak expiration и падения charged
  memory минимум на длину тела. Затем reset weak освобождает control block.
  Прежняя проверка только адреса внутри callback больше не является единственным
  доказательством владения. Обычный body для PUT остаётся пустым.
- Строки 634–644, 673–712: SHA полного logical stream вычисляется отдельными
  protected readers и сверяется с sealed ref. Session/finalize JSON проверяется
  через production jsonObjectFields/jsonArrayValues: roles, sizes, full SHA,
  codec/rate/channels/duration соответствуют холодным данным и прежнему контракту.
  Эталон не выводится из transport result; перед сравнением PUT выполняется Seek.
- Account получен настоящим resolver через fake GET spaces/auth-me; queue row
  и inspectProtected proof настоящие. Нет currentAccount/READY/context/generation
  setters. Native owners создаются, используются и освобождаются на worker.
  Диапазон: actual 3000-frame recording → insertion/adoption → cold proof →
  direct production transport с подменой сети. Result adoption явно pending;
  restart ожидает pending, не uploaded. Scheduler continuation этим не принят.

## Debug proxy: свидетельство и поправка assertions

Прочитан локальный `graf-f200-http307-red.QT91uu/native301-counter-symbols.log`:
PID6336, ARM64 CDB noninvasive examination, строка44 показывает
`CustodyOwnedMemory::bytes_ = 0x10` (16 байт). Журнал содержит checksum warning;
независимая binary/source300 привязка этим review не заявляется.
Это согласуется с process-wide ReadCache, содержащим пустой CustodyBytes
(`ProtectedCustodyReader.cpp:18–31`), и существующим WriteStream-паттерном
(`ProtectedCustodyWriteStreamTests.cpp:478–494`).

Main теста:967–976 заранее измеряет idleOwnedBytes локальным пустым CustodyBytes
и отдельно требует восстановления исходного baseline после его уничтожения.
Все три прежних абсолютных zero assertions (870,979,1002) требуют точного
равенства этому измерению, не допуска/верхней границы или post-failure baseline.
Timeout и production quota не расширены. CRT stderr/abort настройки повторяют
WriteStream-паттерн; assertions и failure exit не отключаются.

Проверка точного diff выполнена без записи: обращение только этих изменений
в памяти восстановило ранее принятый SHA-256
`5bc8ae6e715aa831f5b706f50cc58556e257588b3030069d66213944115382b7`.
Иных изменений относительно принятого body/JSON теста нет.

## Непринятые границы и native status

Source assertions не доказывают включение control block в квоту, allocation
refusal/response/retained-results budget или native WinHTTP lifetime через
ReceiveResponse/cancel/handle-close. Эти проверки и полный prepare/flight/result
commit/adoption остаются открытыми. Intended DI constructor, protected upload
overload, bodyView и protectedBody ещё не реализованы; compile RED ожидается,
но reviewer сборку не выполнял и compilation result не утверждает.

Статусы ниже — последнее сообщение main, не независимо выполненный native run:

- 301 terminal FAIL: Release53/53 PASS, Debug52/53, test_exit8, единственный
  отказ49 на frozen SOURCE300. Завершение asserted PID6336 зарегистрировано
  main отдельно после CDB; это не успешный выход теста. FAIL не переписан в PASS.
- Diagnostic308 targeted RUNNING: baseline SOURCE300 + fix только одного
  тестового файла; не304 и не текущий незавершённый HTTP RED. Target49 Debug,
  затем Release; результата или полного current-source PASS здесь нет.
- 309 PREPARED, NOT RUN; принятия native/full/installed нет.

Reviewer не запускал builds/tests/native jobs/VM/CUA и не менял production,
нормативные checklist markers, tasks или прежние отчёты. Единственная разрешённая
запись — этот новый reviewer-owned файл. FULL T116 и остальные gates открыты.
