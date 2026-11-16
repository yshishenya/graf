# Независимое узкое ревью native playback — 2026-10-01, round135

Статус: APPROVED NARROW по коду исследовательской обвязки и согласованности прочитанных final positive/fault receipts на одинаковых EXE. Только частичное синтетическое доказательство; не независимое воспроизведение runtime, не приёмка продукта или T114 целиком.
Режим: code-reviewer, read-only источники и метаданные; единственная правка reviewer — этот docs-only отчёт. Reviewer не собирал и не запускал тесты, VM, UI, микрофон или устройства.

## Проверенные текущие байты

- PlaybackProof.cpp SHA256 `599ccaf4f02b7102c35c40415ef2682478beda9608d8166f5d39681189a7e898`; ожидаемый EXE `3f80a5f3b83cb259357165886df3a80e21f42833d04decaaf568fff127ed21b5`.
- ContextProof.cpp SHA256 `ebe944228e9349a5781ecece1605f651d6fdd78cbaa9b9c932dac06cf7b244c6`; ожидаемый EXE `aa876c21a7657f84bfa82047f8830491208876935c95598ec6a9009f07ea65f4`.
- context-run.ps1 SHA256 `3be550b7f2b68eea3fe6e6c4c95bf7162a8fc8a82d74543dcd38b89022e45268`; playback-build.cmd `4c7f1e6b1b14fdda0c4e72a03107f7471f434d9336ac1fc8097602eaf2e2faad`.
- Текущая include-зависимость ProtectedMfProof.cpp SHA256 `58e65c6e914d8e54c0b868e4d0e0208225b74de57ed6769c5decebd3c9e8c3a2`: F200_PROTECTED_MAIN отделяет entrypoint от вложенного wmain. Исторические source `141b5a…`/EXE `60cc…` не являются source/build identity нового Playback EXE. /W4 /WX build exit 0 сообщён main, reviewer его не воспроизводил.

## Проверка кода

- PlaybackProof.cpp:10–24,33–46,70–72: callback содержит атомарные значения, не вызывает engine и не держит указатель на стек; COM-ссылки callback/attributes/byte stream живы до Shutdown. На исключении Player выполняет невыбрасывающий cleanup; ProtectedStream сериализует операции mutex. WAITFORSTABLE_STATE не включён, обязательного SetEvent для этого режима нет ([Microsoft event contract](https://learn.microsoft.com/en-us/windows/win32/api/mfmediaengine/ne-mfmediaengine-mf_media_engine_event)).
- Positive oracle: CANPLAY, конечная duration 29.9–30.2 s, audio-only/muted/volume 0, progress, стабильность pause, новые SEEKED + позиция и !IsSeeking для 10→1→tail, два resume progress, ENDED + IsEnded, отсутствие ERROR, Shutdown и MF_E_SHUTDOWN при последующем Play. Sleep/допуски/5 s wait — только параметры generated fixture, не продуктовые пороги.
- Fault: собственные b0-* повреждаются только после validated reopen и проверки всех собственных envelopes; активная версия первого блока входит в этот набор. Предварительного чтения тем же reader нет. Требуются failed SetSourceFromByteStream либо ERROR event, затем sticky STG_E_READFAULT + got 0; первый отказ самого контрольного Read дал бы STG_E_WRITEFAULT и не прошёл oracle. Timeout/любой catch сами по себе не являются expected rejection.
- Fault также требует Shutdown и запрет Play после него. Corroboration фиксирует sticky post-failure HRESULT, не первоначальный HRESULT чтения MediaEngine. cipher_objects в fault — число проверенных объектов ДО намеренного повреждения, не валидность повреждённого набора после него.
- Прежнее замечание P2 закрыто: MFShutdown:96–97 проверяется без исключения за пределами catch, ошибка сохраняет ненулевой exit, CoUninitialize выполняется. Final positive/fault receipts вместе с кодом согласуются с прохождением bytes Close в обеих ветках; reviewer не воспроизводил API-вызовы.
- Context: fixed sibling PlaybackProof.exe, --medium/--medium-fault, private filtered token без global DACL changes; suspended child назначается собственному KILL_ON_JOB_CLOSE Job до ResumeThread, native timeout 35 s. Actual medium/no-admin проверяется внутри Playback до создания данных.
- Runner: PlaybackFault включает Playback; прочие режимы несовместимы; команды фиксированы; оба EXE-хеша проверяются до/после; внешний timeout 45 s, собственный GUID-result, код отказа не маскируется. Новых блокирующих дефектов в рассмотренном коде не обнаружено.

## Прочитанные receipts, без самостоятельного воспроизведения

- Исторический positive `context-result-60540f7c-d54d-42fa-87d8-fcb1bfdb5728.json` относится к прежним EXE `15ec…/0d63…`, Shutdown 15 ms; не переносится на новые байты.
- Final positive `context-result-22abdb51-5358-4f95-b9b2-1bf6ae8ccf31.json`: ожидаемые EXE `aa876…/3f80…`, playback=true/fault=false, exit 0/stderr 0; PLAYBACK_PASS seeks=3/resumed_twice/ENDED, Shutdown 16 ms/post-Shutdown rejection/muted; 366529 logical bytes,6 собственных envelopes,restricted_medium=true,input_devices=false,damaged=false,child exit 0. EOS достигнут после seek к хвосту, не после непрерывного воспроизведения всех 30 s.
- Final fault `context-result-9ea4a118-dd4b-4315-b87e-54a6939c7c40.json`: те же EXE, playback=true/fault=true, exit 0/stderr 0; native_source_hr=0, затем асинхронный ERROR event_hr=0x8003001e/event_error=4; sticky Read rejection + got 0 проверяются кодом, Shutdown/post-Shutdown rejection выполнены согласно выводу, child exit 0. Это expected native rejection повреждённых собственных данных, не успешное воспроизведение повреждённого файла;6 объектов проверены только до повреждения.
- SHA256 прочитанных receipts: positive `42f296875c269eb79b79ca2b9e89bca4bddf9d0aa04bd3e16440da9ef1717a13`; fault `943f0583471af4f158015880496625c2db0de0ca07e7645a390204adde75544f`. Source/runner-хеши повторно совпали после чтения; EXE pre/post равенство обеспечивается прочитанным runner и сообщено main, reviewer не хешировал исполняемые файлы в VM.
- Проверка receipts подтверждает записанные идентичности/вывод и их согласованность с кодом, не является запуском reviewer или самостоятельным доказательством всего поведения ОС. Положительный native MediaEngine путь и ожидаемый отказ после повреждения дают только частичный T114 Phase0 evidence под same-user restricted medium token.

SOURCE IMPLEMENTATION NOT READY. Phase0/Phase1, T114 целиком, clock/storage model, ordinary separate-user account, capture, native product/Home/install playback, SC-003 и полная FR-012 acceptance остаются открытыми. Generated muted output не доказывает слышимое качество; свои envelopes не являются all-disk/temp/pagefile аудитом. Shutdown ms не SC-003; никакие checkbox/task completion, архитектура, migration или protected product code этим отчётом не разрешены.
