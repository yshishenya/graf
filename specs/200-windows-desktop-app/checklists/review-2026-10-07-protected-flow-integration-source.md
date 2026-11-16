# Round276 — SOURCE: только действующий startup защищённого хранилища

Вердикт: **ограниченный SOURCE GO**, C0/H0 в рассмотренном startup-срезе; не GO полного плана Round276/T116.
Полное покрытие отказов и сквозная продуктовая приёмка остаются **NOT GO / pending**; отсутствие реализации следующих этапов не объявлено дефектом startup-среза.
Canonical: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`, `codex/200-windows-followup`, HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; dirty сохранён.
Основание: неизменённый REQUIREMENTS276 `review-2026-10-07-protected-flow-integration-gate.md`, действующие договорённости §5/§8 и план подключения потока; high-risk-product, не облегчённая продуктовая приёмка.
Снимок: `/Users/yshishenya/Documents/graf-f200-integration276-fixed.uz0dTm`; `source276.json`, 207 входов.
SHA карты: `3a5763a192bf101baf9cc429b17e831048df524ba8eaf6fe859cfc76ed4f19bb`; лично сопоставлены canonical/frozen: 0 расхождений.

## Исходники и закрытые замечания

Прочитаны фактические Files/Metadata owner, общий commit-body, QueueService decoder/serializer, NativeCapture worker/ACK/drain, AppMain wiring, CMake и настоящий startup-тест; применены code-reviewer и ponytail-review.
`ProtectedCustodyFiles.cpp:402,462`: root/store/fixed IDs удерживаются native leases; создание только проверенного virgin-root, без подмены отказа repair/fallback.
`ProtectedCustodyMetadata.cpp:979,1034`: BOTH bootstrap/queue проверяются до возврата owner; birth использует общий commit-body и последующую проверку, без release/reopen промежутка владения.
`NativeCapture.h:166,203,624,648`: root копируется до dispatch; worker не захватывает raw this; owner и его native leases освобождаются на worker, UI получает только значения и посылает ACK.
`NativeCapture.h:441`: update drain требует terminal и фактического завершения native thread; отменённое обновление запускает свежую проверку лишь после выхода старого worker.
Конструктор не выполняет custody IO; poll обрабатывает startup completion до закрытого consumer guard. ACK не включает `storageWritable`: запись/HTTP/playback/delete остаются закрытыми.
SRC276-PRE-1 закрыт по исходникам: `validateQueueValue` получает cancellation, общий bounded decoder использует его, ParseCancelled возвращает typed отказ с 995; runtime fault-probe этого нового owner отдельно не доказан.
SRC276-PRE-2 закрыт по исходникам: один private constexpr `emptyLedgerJson` используется serializer и charged birth CustodyBytes; отсутствует прежний uncharged временный набор трёх коллекций/строки.
Logical v2 reader остаётся договорённой совместимостью; это не допуск legacy plaintext-root и не основание запрещать v2 только в этой проверке.
Тестовая коррекция GetLongPathNameW повторяет существующий native fixture: исправлен TEMP 8.3 alias, продуктовый exact-path guard не ослаблен.

## Лично прочитанные экспортированные доказательства

Три полных native raw logs, receipts и readback прочитаны; reviewer не запускал VM/tests и не заявляет собственный NTFS запуск.
Release: build0/test0, выбранные 8/8 PASS; Files 87.83s, настоящий StorageIntegration 0.35s.
Первый Debug: build0/test8, 7/8 PASS, Files Timeout120.02s; в raw нет assert/CRT причины. Этот неуспех сохранён, причина не объявлена установленной.
Debug retry: те же исходники и EXE, без rebuild, диагностический timeout300; 8/8 PASS, Files 267.51s, StorageIntegration 0.35s. Это не доказательство SC/Stop/performance gate.
Release receipt SHA `bd4ba30cab06cbbee4f0bda6744f5cf5fabd869b64aba6792630f55ebed95aeb`; raw `4c0075d57847bb9dc99e68b858fb053aef8f405ad2335902faaff0695a03e2dc`.
Первый Debug receipt SHA `de4ad913acfe2b89b68c4cdd0b3db72b4fb8cdd85152cff7dd20bb8b7d5aac25`; raw `2a21be2e6743133b59302c45c0715a969ebee57bd83e9f38fe96bb9ae1501879`.
Retry receipt SHA `96192c75b8e2f1d9b2a4c802273b26c6c52a1286da213c23947f91816e0b08aa`; raw `b8b792434b5de738ef37215d69d5e46f532b3551f2f253019d713f68bdc658aa`.
`readback276-retry.json` SHA `6b7c0118dbb3604a5617535637dbe375c978df75a3d18d616187e329dfe65f26`: source207/receipts MATCH, 16 actual EXE hashes и PE0x8664, согласно выполненному main readback.
SDKApp build-only: `app276.json` SHA `0e0b1019e5d75fe378f9345e9cdc35eeaf0106518b84aa7bb4c88e7c149d05ab`, Release/x64 build0, тот же source207.
Полный app276-build.log прочитан после UTF-16 декодирования только в памяти; SHA исходных байтов `953b1e7a0d8e7ef7427b2d68300cf5032ed2844432e2df30348711bab16a4d2e`.
App readback SHA `0155f5a02b23ac4272f2c7e2de908818a4a126f5958e436242da5c9b2258c96d`: MATCH207/receipt, EXE `5a9d7fb8cbf1d6291a4cba8d9ec3d571db53a823a6d703e89d259250d501bbf4`, PE0x8664, owned_jobs0.
AEC source/license identity 846fe90a289f58b7c9303a635142aa2c7caa93e5 проверена build guard; D9025/C4100 сохранены, не zero-warning и не vulnerability audit.
Предшествующие harness parse/compile отказы и startup RED сохранены отдельно; они не превращены в PASS этим отчётом.

## Покрытие и предел вердикта

Настоящий класс проверен на birth/BOTHg1, ACK/idempotency, update stop/restart, удержание IDs, cold restart без изменения файлов и независимый BOTH decode после освобождения owner.
`unknownRootIsPreserved` создаёт root с inherited ACL: возможен отказ private-ACL ещё до inventory scan. Доказаны сохранность/закрытость/no custody birth, НЕ конкретная private-unknown inventory ветка.
Эта оговорка не обнаруживает source-дефект startup-кода и не отменяет узкий SOURCE GO, но запрещает закрывать полную матрицу inventory/fault acceptance.
Новые owner allocation/cancel/read/commit fault cuts, частичный birth/публикация и branch-specific private unknown inventory требуют отдельного доказательства; старые Files/Candidate cuts не подставлены вместо них.
Typed queue mutations/durable completion/adoption, полный protected V5→sealed→queue ACK→restart→HTTP/playback/delete, account/epoch/currentness и открытие глобальной готовности не приняты.
T116, H250, physical/installed acceptance, legacy AAC RED, performance и release остаются открытыми; выбранные 8 тестов не whole-suite GREEN. App не установлен/не запущен, устройства/профили/сервер не использованы.
До записи: 161 Markdown = 10 текущих нормативных списков (154 checked/0 open) +151 исторический отчёт; исторические находки не переклассифицированы в текущие checklist obligations.
Tasks 120/93/27, SHA `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`; markers не меняются. Единственная запись reviewer — этот новый отчёт, 0 checkboxes.
Ponytail: нет безопасного сокращения без потери владения/отмены/ACK; переиспользуются native leases, общий commit и decoder, без второго framework. `net: -0 lines possible.`
