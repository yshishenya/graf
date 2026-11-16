# Узкая независимая проверка стенда T114 — 2026-10-01

Область: только три исправления disposable generated-data `ProtectedMfProof.cpp`
относительно ранее проверенного SHA `dd6e1c0a37b778adff8ecba6149cf89704acb646d4c19d0cf4551098ad765237`.
Применён code-reviewer; продуктовый код, формат хранения и остальные задачи не проверяются.
Вердикт: **CLOSED AT SOURCE — все три замечания устранены в коде**.
Новых блокирующих замечаний в этих исправлениях не обнаружено; общий допуск F200 не выдаётся.

1. Строка 257: both-invalid принимает только `reopen-validated-index` через strcmp;
   любое другое std::exception пробрасывается и не засчитывается как ожидаемый отказ.
2. Строки 183–187, 250, 256: verifyPattern проверяет exact Stat length и все bytes
   canonical 3840123 и fallback 3670016, включая хвост, порциями не более 64KiB.
   Каждое чтение требует полного count и совпадения с pattern; прежние 64 ranges сохранены.
3. Строки 19, 42, 253, 267: имя indexPublishMaxUs/index_publish_max_us соответствует
   таймеру publish(), не включает шифрование/запись блока и не объявляет полный checkpoint/Stop.

Локально прочитаны и сверены SHA256:
Source: `141b5a293748703bf52fc50ce5d8c92a6f6df39c6a9f8fe389023e1c40b2f490`.
EXE: `60ccffd7a3daa6cc5607e1213a4af4e97ec90ea8248df697aab5a0b1cdd728ea`.
Runner: `d5d05ba57657ab413bc39cf2a047b291244779d4d18b6d30820e86bc7187250b`.
Runner требует именно этот EXE hash. Build /W4 /WX exit0 сообщён main, самостоятельно не выполнялся.
Main сообщил новый exact PASS для source/EXE/runner выше; reviewer самостоятельно его не воспроизводил и не принимает runtime. Прежний PASS другого source/EXE не подменяет этот результат.

Ограничения: собственные DPAPI files, не весь диск/временные файлы MF; SourceReader decode/seek,
не MediaEngine/UI playback; private delta не peak, elapsed не Stop; без GC, migration,
adversarial и power-loss proof. Restricted-medium на прежнем EXE `1c511c7fa517ec3a38ea41e741227eb9b7fc7a5a9c365d1891c83b67b1a60282` завершился 0xc0000142 без вывода;
standard-user proof отсутствует, отдельная nonadmin account не испытывалась.
**SOURCE IMPLEMENTATION: NOT READY.** T114, Phase0/Phase1 и protected-storage code не принимаются.
Изменён только этот reviewer-owned отчёт; отметки не поставлены, source/VM/UI/тесты не изменялись и не запускались.

Дополнение main после проверки кода: указанные выше exact source/EXE/runner прошли запуск exit0/stderr0; reviewer самостоятельно не запускал и журнал независимо не проверял.
Сообщены canonical full_identity 3840123 bytes + 64 ranges/15 checkpoints, index_publish_max_us=57221, stop_tail_us=6279; fallback full_identity 3670016 bytes и expected-exception assertion PASS.
MF: 366529 logical bytes / 2881536 decoded bytes, два SourceReader seek, child exit0, четыре checkpoints/два rewrites, index_publish_max_us=6573; private_delta=7852032 не peak, elapsed=4376ms не Stop.
Закрытие трёх замечаний по коду сохраняется; новый standard-user результат не заявлен, ограничения и NOT READY выше неизменны.
