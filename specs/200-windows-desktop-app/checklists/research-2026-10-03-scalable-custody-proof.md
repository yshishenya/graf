# Исследование: масштабируемое доказательство protected custody

Дата: 2026-10-03. Статус: ненормативное предложение для решения владельцем T115; не принятие архитектуры, не прототип и не доказательство производительности.

Канонический worktree: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`. Исследование выполнено отдельно от текущей работы над CNG pseudo handles. В рамках этого отчёта не изменялись код, контракт, plan/tasks или Git; не запускались сборки, тесты, запись звука либо приложение. Единственная запись — этот новый документ. Ниже приведены выводы из текущего исходного кода, расчёты объёма работы и предложение; расчёт не подменяет измерение Windows.

## 1. Решение в одном абзаце

Для больших `canonical/media/playback` объектов предлагается формат v2: один зашифрованный контейнер на объект/роль, один непрерывно удерживаемый и проверенный Windows HANDLE, неизменяемые добавляемые DATA и узлы трёхуровневого дерева индекса, две небольшие защищённые ячейки публикации. Новые записи шифрует Windows CNG AES-GCM; ключи эпох защищает user-scope DPAPI. ACK заново проверяет обе ячейки, новые записи и переход от ранее доказанного корня, но не перечитывает неизменившиеся DATA. После любого разрыва владения требуется полная потоковая проверка достижимого содержимого обоих корней. Это устраняет квадратичную работу при захвате и полное копирование индекса, однако **изменяет принятую семантику свежей полной проверки на каждом ACK**. Без предварительного изменения T115 это не допустимая оптимизация.

Минимальное предложение не меняет формат ограниченных v1-метаданных, UUID, logical v5 bytes, хеши/диапазоны загрузки, сроки удаления, пределы очередей или допуски захвата. Оно не даёт мгновенную полную проверку 64GiB после перезапуска и не обещает постоянное время физического I/O при отказе диска.

## 2. Почему одних микрооптимизаций недостаточно

Источники горячего пути:

- [ProtectedCustodyWriter.cpp:165](/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup/apps/windows/RecApp/Storage/ProtectedCustodyWriter.cpp:165): `writeAt` вызывает `checkpoint()` после каждого полного canonical блока 256KiB, строка 179.
- [ProtectedCustodyWriter.cpp:223](/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup/apps/windows/RecApp/Storage/ProtectedCustodyWriter.cpp:223): полный candidate index шифруется; после публикации `readValidatedSnapshot()` в строке 247 перечитывает содержимое до ACK в строке 257.
- [ProtectedCustodyFiles.cpp:477](/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup/apps/windows/RecApp/Storage/ProtectedCustodyFiles.cpp:477): два slot читаются/декодируются в строках 491–500; все DATA refs каждого проходят `readBlock` в строках 503–514. Native/hash/ACL/unknown-I/O отказы не разрешают переход к другому кандидату, строки 518–522.
- [ProtectedCustodyCodec.cpp:216](/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup/apps/windows/RecApp/Storage/ProtectedCustodyCodec.cpp:216): сериализация, хеширование и защита всего плоского индекса; decode в строке 236 снова создаёт полный массив entries.
- [ProtectedCustodyFiles.cpp:280](/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup/apps/windows/RecApp/Storage/ProtectedCustodyFiles.cpp:280): физический read сам проверяет блок, возвращая ciphertext; [ProtectedCustodyReader.cpp:95](/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup/apps/windows/RecApp/Storage/ProtectedCustodyReader.cpp:95) и writer `loadDirty/readAt` затем декодируют его ещё раз. Это отдельная избыточность потребителя, не причина дополнительного второго decode каждого resolver ref.

При последовательной записи checkpoint N содержит N и N−1 DATA refs: проверяются `2N−1` блоков. При 64MiB это 511 refs на последнем ACK; сумма для 256 checkpoints — 65 536 refs, то есть 16GiB payload-проверок, без дополнительных проверок записи/индексов. Это вычисление по алгоритму, не новый тест. Предоставленное существующее synthetic VM измерение: последний `writeAt` 3.423817s против прихода 256KiB за 1.365s при 48k mono Float32, около 2.51×.

Дополнение от основного агента после pseudo-handle probe, полученное при завершении отчёта:64MiB total217694.997ms, lastWriteAt checkpoint1435.316ms против incoming canonical cadence1365.333ms; reads132351, hashCreates67583, generation256, committed256, errors0, ownedRelease0. Сообщённые проверки:36Windows/35host/VS0. Это предоставленные результаты, здесь они не воспроизводились и не проверялись запуском. Last checkpoint остаётся выше cadence примерно на5.13%; total не улучшился против сообщённого183810.168ms before. Нулевые errors и committed256 не доказывают sustained capture. Эти числа не принимают v2 и не меняют структурный вывод O(N²).

При 64GiB N=262 144: последний ACK проверяет почти 128GiB, сумма до него — 16PiB payload-проверок. Дедупликация одинаковых refs между двумя slots уменьшает коэффициент примерно вдвое, но оставляет O(N) на ACK и O(N²) за запись. Переиспользование CNG provider, удаление повторного decode и лишних копий полезны, но не меняют эту зависимость. Полная свежая проверка каждого ранее принятого байта и длинонезависимый ACK противоречат друг другу; криптографический хеш сам по себе не доказывает, что старые байты сейчас читаются с диска.

## 3. Граница Windows-доказательства

### 3.1. Один настоящий владелец файла

Предлагаемый `GuardOwner` содержит один private, non-inheritable контейнерный HANDLE с `GENERIC_READ | GENERIC_WRITE | READ_CONTROL`, `FILE_SHARE_READ`, `FILE_FLAG_OPEN_REPARSE_POINT`; для позиционного асинхронного I/O — также `FILE_FLAG_OVERLAPPED`. Новое создание только `CREATE_NEW`, существующее — `OPEN_EXISTING`, никогда `CREATE_ALWAYS/TRUNCATE_EXISTING`. До первой записи применяются и проверяются user-only ACL, как в текущем backend. Этот HANDLE не передаётся наружу; reader получает только read capability, writer — отдельное отзываемое разрешение изменять объект.

Windows документирует исключение конфликтующего write/delete доступа, действие sharing до закрытия HANDLE и отказ открытия при несовместимой writable mapping. Проверка совместимости двусторонняя. Поэтому отдельный reader `GENERIC_READ + FILE_SHARE_READ` несовместим с уже открытым RW writer; минимальный вариант использует общий владелец и позиционные чтения, а не новые HANDLE на каждый reader/блок. [S1]

Сохраняются удерживаемые ancestor handles и store/object identity handles. Текущая опора: [ProtectedCustodyFiles.cpp:116](/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup/apps/windows/RecApp/Storage/ProtectedCustodyFiles.cpp:116), `inspect/openFile/lockDirectory/identity`, строки 116–169. Проверяются actual final path, fixed local volume с ACL, disk-file type, отсутствие reparse, `nNumberOfLinks == 1`, private DACL, store/object/container IDs и нативная идентичность файла. Volume/file ID идентифицирует файл, но не версию его содержимого. [S8]

Перед ACK и при выдаче read capability повторяются ограниченные проверки native identity/path/ACL/link-count. Блокирующий или неуспешный native check означает отказ, не ослабление режима открытия. Число проверок зависит от фиксированной глубины пути, не от числа DATA.

### 3.2. Чего HANDLE не доказывает

Это исключение обычной внешней записи/замены **удерживаемого основного потока** файла при корректной работе Windows, а не абсолютная неизменяемость файловой системы. Доступ к attributes/extended attributes не исключается sharing; режим sharing относится к отдельному stream. Нельзя объявить невозможными изменение DACL, появление hard link/ADS или вмешательство privileged/raw-volume/filter-driver. Проверка этих условий не является атомарным запретом любых будущих изменений. [S1, S6, S7]

Мы не создаём mappings, ADS или hard links. Неожиданный data stream проверяется ограниченным перечислением с немедленным отказом при первом лишнем stream, без накопления списка; невозможность безопасной проверки — отказ. Для перечисления по имени сохраняются ancestor ownership и проверка того же file ID. Hard-link alias разделяет содержимое того же файла; обнаруженное число ссылок не равно одному — `unsafeFile`, а не повод обходить guard. Native regression отдельно должна подтвердить поведение уже существующей mapping, alias, rename/reparse и изменения ACL. [S6, S7]

Собственный RW HANDLE позволяет своему backend перезаписать старые байты. Поэтому append-only — инвариант реализации, не новое свойство Windows: единственная разрешённая запись вне EOF — одна из двух commit cells. Нужны отдельные методы append/head-write, проверяемые диапазоны и регрессии на запрет записи в опубликованный DATA/node/key capsule. Ни byte-range locks, ни file ID, ни mtime не заменяют эту границу.

Диск может испортить старый блок при удерживаемом HANDLE. Тогда очередной ACK, наследующий прежнее доказательство, может ещё не обнаружить порчу; последующее чтение обязательно обнаруживает её до выдачи байтов. Это материальное изменение времени обнаружения относительно сегодняшнего полного resolver. Если T115 требует обнаруживать **любую** такую порчу до каждого ACK, этот проект следует отклонить: ограниченного эквивалентного доказательства нет.

### 3.3. Владение переживает writer, а не процесс

`GuardOwner` совместно удерживают writer, независимые IStream readers/Clone, finalizer, upload/read jobs, retained results и незавершённые native operations. Каждый логический reader имеет собственные cursor/root generation и отдельный pin; общего пользовательского file pointer нет. Writer release/Stop отзывает только write capability. Последний фактический владелец закрывает HANDLE после завершения всех I/O и стирает ключи; только затем отпускается custody pin, как текущий порядок State в [ProtectedCustodyWriter.cpp:29](/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup/apps/windows/RecApp/Storage/ProtectedCustodyWriter.cpp:29).

Нельзя выполнить close/reopen RW без разрыва доказательства. Для ACK предлагается independent positioned readback тем же удерживаемым HANDLE, с освобождёнными writer cipher/plain copies, а не фиктивный «validated reopen». Это отдельно требует изменения T115. Дублированный HANDLE не нужен минимальному варианту; отдельные процессы не получают право доверять RAM proof token. Cross-process writer/reader coordination не объявляется решённой этим дизайном.

## 4. Формат v2: packed records и постоянное дерево

### 4.1. Область применения и расположение

Один фиксированно названный `content.packed-v2` в уже ограниченном каталоге большого объекта/роли. `canonical`, `media`, `playback` имеют отдельные объекты; это не один файл на весь application store. Queue/bootstrap/manifest/recovery/package-state/delete/migration остаются в действующем v1 DPAPI формате с полной проверкой ограниченных metadata slots/blocks. Формат выбирается явно из защищённой authority: ошибка v2 никогда не переключает чтение на v1/plaintext.

Контейнер содержит небольшой технический header с format/store/object/container ID, две независимые фиксированные head cells по 16KiB и область добавляемых записей. Header не содержит аудио, logical SHA, пользователя, private URL или plaintext ключа. Контекст header проверяется по DPAPI heads/capsules. Head cell имеет ограниченную framing length и DPAPI envelope с zero reserved/padding checks; root descriptor plaintext не сохраняется отдельно.

**Файл не является буквально полностью append-only:** две head cells перезаписываются по очереди; DATA, tree nodes и key capsules только добавляются. Это явное исключение. Чистый бесконечный commit log без фиксированных heads потребовал бы поиска последнего commit по истории/EOF либо дополнительного указателя и нового crash-proof; для минимального решения не выбран.

Root descriptor включает slot, generation, logical length≤64GiB, block size/count, tree parameters, root offset/exact envelope length/ciphertext SHA-256, committed extent, format и IDs. Logical SHA остаётся в защищённых metadata/finalized descriptors по существующим правилам; ciphertext hash не подменяет его. Два небольших descriptor заменяют две плоские index copies около 8MiB у предельного объекта.

### 4.2. Три уровня для всего принятого диапазона

Radix 64: root → branch → leaf → DATA. `64³ × 256KiB = 64GiB`, ровно 262 144 logical blocks. Узел имеет 64 entries по предложенным 64 bytes, то есть 4096 bytes entries; с заголовком, CNG framing, tag и выравниванием его physical envelope ограничивается 8KiB. Точный wire layout ещё должен быть принят в T115, это не готовая спецификация.

Предлагаемый child ref: offset u64, physical envelope length u32, DATA payload length u32, SHA-256 точного child envelope 32 bytes, flags u32, reserved u32, record version u64. Получается 64 bytes. Node level/base logical range входят в authenticated context; диапазон ребёнка выводится из позиции и проверяется, а не доверяется произвольной ссылке. DATA version — уникальная физическая позиция записи внутри container ID, не переиспользуемый generation.

Все integer fields имеют фиксированную LE-сериализацию; sizes/counts/offset addition проверяются до allocation/read. Child record расположен раньше parent, полностью внутри committed extent, имеет точные type/context/range/length и ожидаемый hash. Key capsule тоже расположена раньше использующей её записи. Запрещены циклы, alias чужого logical range, ссылки на heads/header/незаписанный хвост, неизвестные enum/flags и ненулевые reserved. Hash покрывает весь child envelope, включая routing header; capsule hash/ref дополнительно связан с authenticated record header/AAD.

ZERO — явный аутентифицированный флаг leaf/subtree с каноническим пустым ref, применяемый только как результат разрешённого `SetSize`. Missing/invalid DATA или неизвестный ref не превращается в ZERO. Дерево с такими subtree entries позволяет представить большой zero extension без 262 144 allocations. Shrink/extend удаляет старые refs из нового корня и заново формирует граничный tail, чтобы удалённые байты не проявились при повторном расширении. Эта новая форма ZERO тоже требует поправки T115.

Один append/rewrite DATA меняет только leaf, branch и root: одна DATA и три новых nodes; старые nodes остаются для двух heads и pinned generations. Для группы≤4 dirty blocks — максимум четыре DATA и 12 nodes, меньше при общих ветвях. Range shrink/zero extension работает по фиксированным boundary paths и entries узлов, не по каждому DATA диапазона. Большой пользовательский Write всё равно разбивается на существующие chunks≤256KiB; это не обещание O(1) для произвольного объёма Write.

### 4.3. Ключи и nonce: не собственная криптография

Каждая DATA/node — отдельный AES-256-GCM record через BCrypt, 128-bit tag, 96-bit nonce. Согласуются и проверяются native tag/key-object properties; вся структура `BCRYPT_AUTHENTICATED_CIPHER_MODE_INFO` и output живут до конца операции. Payload SHA-256 сохраняется внутри защищённого DATA. Ошибка `BCryptDecrypt`, включая `STATUS_AUTH_TAG_MISMATCH`, не выдаёт plaintext, даже если API уже заполнил output buffer. [S3]

DEK — 32 случайных bytes от проверенного `BCryptGenRandom(NULL, ..., BCRYPT_USE_SYSTEM_PREFERRED_RNG)`. Он хранится только в учтённой памяти/CNG key object и в добавленной user-scope DPAPI capsule≤16KiB: key, IDs, role, key epoch, capsule offset, format и usage policy. Entropy/context привязываются к store/object/container/role/epoch; `CRYPTPROTECT_UI_FORBIDDEN`, без `CRYPTPROTECT_LOCAL_MACHINE`. DPAPI защищает данные ключа и их целостность; это не защита от полного отката store. [S4, S5]

Свежий DEK создаётся при **каждом** новом writable acquisition после разрыва guard и при ротации внутри него. Старые unwrapped epochs используются только для decrypt, никогда снова для encrypt. Один worker резервирует возрастающий counter **до каждого** encrypt вызова всех типов записей; nonce — фиксированное 32-bit поле контекста этой единственной encrypt-сессии ключа плюс 64-bit counter. Failed/cancelled попытка тоже расходует counter; retry не создаёт другой ciphertext с тем же nonce. Heads используют DPAPI, а не GCM с повторяемым slot nonce.

Предлагаемая инженерная граница эпохи: сменить ключ до 1GiB суммарного plaintext плюс AAD, либо до 2²⁰ encrypt attempts, что наступит раньше; учитывать nodes и неуспешные вызовы. Это предлагаемые ограничения для проверки криптографическим reviewer, **не утверждение, что NIST сертифицировал именно эти числа или новый составной формат**. Счётчики не wrap/reset; невозможность получить свежий ключ блокирует запись. NIST требует уникальность пары key/IV, рассматривает fresh key после потери состояния и не даёт GCM встроенной защиты от replay. [S2, §§8–9, Appendix D]

Так не нужно угадывать persisted nonce high-water mark по orphan records: после crash появляется новый ключ. После восстановления полной VM/RNG state свежесть системной случайности этим дизайном не доказана; полный rollback остаётся за принятой границей угроз. Capsule нельзя объявить crypto-erasure механизмом: retained roots продолжают нуждаться в старых ключах.

Общий cache держит не более восьми decrypt epochs с собственным byte budget; cache miss читает/unwraps одну bounded capsule по прямому ref, не сканирует список эпох. Все текущие encrypt/decrypt key objects резервируются до создания, уничтожаются после actual completion. Key-object memory учитывается по queried length с пределом; native внутренние allocations отдельно измеряются. По первому authentication/native failure контекст прекращает работу, без бесконечного перебора/повторного oracle. Cached DEK может оставаться пригодным после изменения DPAPI master-key state: немедленное отозвание уже расшифрованного ключа не обещается. Любая наблюдаемая DPAPI/CNG/account capability ошибка остаётся fail-closed; новые checkpoints всё равно требуют DPAPI heads.

## 5. Минимальное доказательство ACK

### 5.1. Что считается установленным доказательством

RAM token корня: `(GuardOwner lifetime ID, native file identity, container ID, root descriptor/hash, generation, length, extent, proof kind)`. Он создаётся только после полной проверки или после проверенного перехода от уже доказанного корня при непрерывном guard. Это ограниченный объект состояния, не per-block bitmap/handle cache и не сериализуемый «verified=true». Передача токена другому native ownership epoch запрещена.

Основание индукции: новый `CREATE_NEW` контейнер с проверенными identities и двумя независимо DPAPI-защищёнными равными empty g1 heads; либо существующий контейнер, полностью проверенный под уже удерживаемым guard. Для v2 аудио предлагается явно разрешить birth pair g1, сегодня такое равенство запрещает audio resolver в [ProtectedCustodyFiles.cpp:524](/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup/apps/windows/RecApp/Storage/ProtectedCustodyFiles.cpp:524). Неполный birth не дописывается автоматически и не становится новым пустым объектом при restart. Empty media root не означает пустой queue/delete ledger или sealed package.

Шаг индукции: старые refs сохраняют **ранее установленную** проверку при непрерывном исключении обычной внешней записи; новый корень проверяется по изменённым paths и точным неизменившимся child refs старого корня. Нельзя принять произвольный root со словами «его subtree уже проверен»: worker должен сверить bounded structural diff с базовым доказанным path. Новая length/zero/range операция тоже проверяется по этому переходу. Всё новое содержимое реально перечитывается и расшифровывается.

Это доказательство происхождения/структурной целостности подтверждённых bytes в принятой модели владения. Это **не свежая полная проверка читаемости всех старых bytes**. Cold/full proof и inherited/live proof должны различаться в документации, даже если оба после согласованной поправки разрешают normal logical operation. Любая выдаваемая DATA отдельно проверяется по root path, AES-GCM и logical payload SHA.

### 5.2. Порядок commit

1. Зафиксировать account/package lease и базовый root; до allocation зарезервировать owned memory, dirty group, pin и физический peak/reserve. Один writer на объект; проверка generation overflow. Если dirty не менялся, прежний commit не превращается в фиктивную новую публикацию.
2. Сформировать DATA и три COW nodes; при необходимости добавить новую key capsule. Append только после actual EOF, с безопасным выравниванием; не truncate/reuse даже невыбранный orphan tail. Children/capsule пишутся до parents, каждое I/O≤256KiB. Удерживать buffer/key/OVERLAPPED/job до completion.
3. Дождаться записи всех records, вызвать `FlushFileBuffers` на том же контейнере. Отдельно перечитать новые records и проверить crypto/hash/context/bounded structural diff; writer payload/cipher copies после этого освобождаются, остаются только небольшие expected refs. На этом этапе head ещё не изменён; отказ не даёт нового commit.
4. Сформировать маленький DPAPI root descriptor. Начало **первой записи** target head cell означает `ambiguous` до завершения reconciliation, независимо от returned write count. Slot для следующей generation — `(generation−1)%2`. Завершить head write и второй `FlushFileBuffers`; ни sector atomicity, ни atomic 16KiB overwrite не предполагаются.
5. Independent positioned readback обеих head cells: DPAPI/context/slot/generation/exact candidate equality; снова bounded check новых DATA/nodes и native identity/path/ACL. Другой head должен совпасть с удерживаемым ранее доказанным descriptor, не просто иметь похожий generation. Новая публикация наследует только refs доказанного base; unexpected transition — conflict.
6. Только после всех этих действий выдать `committed` ACK и заменить RAM root token. Ошибка после начала head I/O — terminal ambiguous, запрещены next generation/GC/normal effects; удерживаются owners/artifacts для отдельного full reconciliation. Отмена/stale callback не стирает фактическую публикацию.

Два flush оставлены намеренно: records до head, затем head до ACK. Small head DPAPI/readback не содержит полного индекса. Число операций/байтов постоянно для одного полного блока; длительность flush/OS scheduling не имеет универсального верхнего предела. Microsoft требует write access для file flush; volume flush требует admin и не входит в проект. Дополнительных power-loss гарантий оборудования, сверх сегодняшней оговорки T115, здесь нет. [S9]

### 5.3. Restart и cold open: выбран полный проход

После закрытия последнего guard, crash, ambiguous commit или новой acquisition **все RAM proof tokens недействительны**, даже при прежнем file ID/mtime. Сначала получить проверенный HANDLE; затем fresh decode двух heads и streaming DFS всех достижимых DATA/nodes/capsules обоих snapshots. Глубина дерева три, память ограничена; можно повторно проверять общие refs, чтобы не создавать O(N) dedup bitmap. Непривязанные orphan records не являются authority, их не надо перебирать для выбора root/nonce.

Проверка выбирает root только по согласованным защищённым descriptors, не по EOF/mtime/«самому большому offset». Auth/native/hash/ACL/unknown-I/O failure не маскируется старой generation. Правила singleton, семантических конфликтов и trusted prefix задаются явно для v2; metadata v1 сохраняет запрет rollback к предыдущему ledger. До разрешённой полной проверки соответствующего контекста нет normal capture/resume/upload/GC admission. Это не новый startup timeout и не обход существующих global queue/delete/migration barriers ради новой записи.

Стоимость cold verify — O(достижимых bytes), вплоть до двух снимков по 64GiB; память O(depth + block). Первая выдача полного verified reader после ownership gap не может одновременно быть мгновенной и fresh-full. После establishment дальнейшие seek/read bounded. Это цена минимального решения, без фонового доверия непроверенным файлам.

Альтернатива «на restart проверять только heads, DATA лениво по seek» не выбрана. Она требует новой provisional/per-range authority, переносит обнаружение порчи старого содержимого на первое чтение и запрещает ссылкам такого root выдавать normal/sealed/delete/GC authority до full verification. Если владельцу нужна именно быстрая cold-first-seek, это **ещё одна** отдельная поправка T115, не бесплатное следствие дерева.

## 6. Seek, Stop, ресурсы и асинхронная ownership

| Параметр | Предлагаемая граница и последствия |
| --- | --- |
| 64GiB logical range | Три уровня radix64; не новый product/server duration cap. Старые device/retention/disk policy сохраняются. |
| Один full-block checkpoint | Append≤256KiB+4096 bytes DATA framing, плюс≤3×8KiB nodes; итого≤284KiB без редкой capsule≤16KiB. Два 16KiB head readbacks и одна head write, два file flush; новые records перечитываются дважды, но не старый payload. |
| Холодное block read после proof establishment | ≤3 node envelopes + одна DATA +≤4 capsules при всех key-cache misses. ≤348KiB physical bytes для полного блока по выбранным caps, каждый read≤256KiB. Structural/native checks — ограниченное дополнительное число операций. |
| Память корней | Нет двух flat arrays/candidate copies. ≤32 pinned root stamps, целевой stamp≤4KiB, то есть≤128KiB; дополнительно≤2 head descriptors на active object, ≤256KiB при32 objects, плюс ограниченные owner/job fields. Не 32×8MiB индексов; всё входит в owned64MiB. |
| Process owned memory | Прежние64MiB с admission до allocation, включая buffers, tree paths, native key-object backing, expected refs, cache, upload/CopyTo/hash. Native DPAPI/MF/provider internals отдельно измеряются. Borrowed output считается до операции; caller lifetime сохраняется. |
| Общий cache | Прежний plaintext предел2MiB; предлагается включить туда также decoded node/key cache: например7 DATA blocks=1.75MiB, nodes≤128KiB и key cache≤128KiB. Каждый объект capacity-counted; нехватка — eviction/отказ, не рост. |
| Dirty и pins | ≤4 DATA blocks/1MiB в одной dirty группе; ≤32 process pins для writer/readers/Clone/jobs/retained owners по [ProtectedCustodyMemory.h:14](/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup/apps/windows/RecApp/Storage/ProtectedCustodyMemory.h:14). Не обещаются32 readers сверх writer/jobs. |
| Native handles | Один container HANDLE на active object, не один HANDLE на весь процесс. Число objects ограничено pins; сохраняются identity/ancestor handles. Ни FD, ни key/node cache не растёт пропорционально числу блоков. |
| Concurrent operations | Предлагаемый дополнительный верхний предел4 native read/write jobs на процесс, с отдельными reserved buffers/key handles, в существующем bounded worker admission. Не увеличивать queues/results≤32 или dispatcher256/254+2EOS. Writer получает обслуживание между bounded read chunks; bulk verify/hash не держит giant lock до конца файла. |
| Seek | Изменение logical cursor O(1); путь к DATA≤3 nodes. Clone имеет независимый cursor и тот же root owner, read-only Write/SetSize/Commit поведение не меняется. |
| Stop | Tail commit≤1 canonical block, либо существующая dirty group≤4, плюс уже принятой bounded очереди; не full recording scan. WAV/AAC/hash/finalize всё ещё O(N) и выполняются async под lease/guard. Stop возврат не равен Saved/normal upload. |
| Disk | Последовательные64GiB дают≤71GiB DATA+node append area по верхним caps, плюс header/heads/capsules и filesystem allocation rounding; это расчёт overhead, не разрешение превысить device policy. Rewrites, failed attempts и orphans добавляют отдельный фактический peak. |

Верхние физические оценки предполагают согласованный wire cap, а не фактический benchmark или лимит NTFS allocation. `min(10GB, 10% capacity)` reserve, существующие5GB/retention7days/80%/95% и все pinned/orphan bytes продолжают ограничивать admission: representational64GiB не обещает хранение64GiB на устройстве с меньшим product budget. Full restart DFS использует несколько node buffers и один DATA buffer; число эпох на диске может расти, RAM key cache — нет.

Контейнер не компактизируется и не hole-punches при активных/pinned roots. GC удерживает целый файл, если любой из двух heads, pinned generation, package-state или исторический delete/migration intent ещё на него ссылается. Append garbage растёт линейно с фактическими изменениями; repeated random rewrites рано или поздно вызывают disk admission failure. Online per-block GC не переносится автоматически из старого формата. Cold compaction могла бы копировать в новый container ID, full verify, durable authority switch и ждать pins, но **не входит в минимальный T116 шаг**.

Overlapped request удерживает `GuardOwner`, pin, key, buffer, event/OVERLAPPED и completion receiver до реального результата. `CancelIoEx` только запрашивает отмену; операция может завершиться нормально, отменой или иной ошибкой. Timeout не освобождает память и не закрывает HANDLE. [S10] Shutdown/Stop/account epoch fences запрещают новые эффекты, но retained job доживает до actual completion. Это сохраняет асинхронное фактическое владение, а не привязывает жизнь ресурса к UI callback.

Нет требования plaintext file/temp/key spill. Контролируемые buffers очищаются при failure/eviction/final release. Как и у действующего DPAPI пути, отсутствие plaintext в application files не означает криптографическое доказательство отсутствия plaintext в OS pagefile/hibernation/crash dump/process memory; если нужна такая более сильная модель, это отдельное противоречие, не решаемое packed layout.

## 7. Матрица отказов и обязанностей

| Событие | Обязательное поведение и граница доказательства |
| --- | --- |
| Уже открытый writable handle/mapping; sharing conflict | Guard acquisition fails; не добавлять SHARE_WRITE/DELETE, не продолжать без защиты. Native gate проверяет retained mapping после закрытия исходного mapping file handle. |
| Внешняя запись основного stream через обычный handle/alias | При непрерывном guard ожидается sharing refusal; вся выдача DATA всё равно authenticated. Kernel/admin/raw-volume вмешательство не покрывается. |
| Rename/delete/ancestor replacement/reparse/path or identity mismatch | Не следовать новому пути, sticky unsafe context, retain artifacts. Native inspection по actual handle; ancestor ownership не заменяется lexical path check. |
| Новая hard link/ADS/DACL/attributes mutation | Не утверждать, что sharing исключил всё; обнаруженный unsafe state либо ошибка проверки блокируют ACK/reads/effects. Ничего не читать из ADS и не «чинить» ACL/aliases автоматически. |
| Собственный backend нарушил append-only | HANDLE это не предотвратит. Forbidden offset/type checks обязаны отказать до I/O; corrupt published bytes требуют fail-closed, не новой proof token. |
| DPAPI/CNG/RNG/hash/key-object failure или GCM tag mismatch | Не выдавать частичный plaintext, output wipe/bytesRead0, sticky failure, не выбирать другой slot ради normal success. В native failure нет разрешения превратить DATA в ZERO/prefix. |
| Disk full/short append/cancel до первого head write | Нет нового commit; прежний acknowledged root сохраняется, tail/capsules/nodes — orphan. Не truncate/reuse offsets или nonce. Проверка reserve не гарантирует успешный write. |
| Начался head write; short/torn write, flush/readback failure | `ambiguous`; никаких next generation/GC/normal effects. Удержать artifacts/actual jobs; новый независимый full reconciliation определяет факт, не optimistic retry. |
| Cancel/stale epoch после начала publication | Довести actual completion/reconciliation до committed либо ambiguous. Старый callback не меняет current logical UI/account capability и не удаляет опубликованные bytes. |
| Crash/power loss | Проверка обоих heads и всего reachable closure после нового guard; corrupt native/auth failure не маскируется старым slot. Не заявлять атомарность sector/head или универсальную durability носителя. |
| Writer release при readers/Clone/finalizer/upload | Сохранить тот же HANDLE и root pins; revoke writes, не proof. Last actual release закрывает и инвалидирует всё доказательство. |
| Повторное open того же FileId/mtime после last close | Full verify заново; никаких persisted verified-bit или cached snapshot из прошлого lifetime. Старые DEK decrypt-only, новый encrypt epoch. |
| Скрытая порча прежнего DATA при live guard | Может не выявиться следующим incremental ACK; выявляется при DATA read/full verify до выдачи байтов. Это требующая принятия потеря fresh-all-data detection на каждом ACK. |
| Повреждение metadata/delete ledger или его referenced authority | Весь соответствующий v1 контекст блокируется, никакого previous empty ledger. Ссылки на v2 имеют точный container/root stamp; cold sealed root fully verifies до authority, live inherited proof допускается только после явной поправки. |
| Trusted prefix для canonical/media | Только отдельно проверенный непрерывный prefix, degraded, длина по1920 bytes, без padding/repetition; no upload/next generation/GC. Native/auth unknown error — отказ, не разрешение prefix. Playback/metadata не получают новый fallback. |
| Полный откат корректного контейнера и всех metadata | Authenticated generation не обнаруживает полный replay без независимого monotonic trust anchor. Сохранить принятое исключение rollback; offline/current-user/no-admin не превращать в обещание внешнего счётчика. |
| Delete/purge при живом job или зависшем I/O | Intent ACK → close admission/cancel → actual quiescence → OS absence → removed ACK. Timeout не означает removed; нельзя force-close guard ради обхода pin или раннего удаления. |
| Большой SetSize/seek/rewrite | Только bounded tree paths/explicit ZERO и новые boundary tails; отсутствие старого DATA не становится нулями. Переполнение/лимит/ресурсы — отказ до принятия изменения. |
| Исчерпан disk budget старых nodes/versions | Admission blocked, сохранить authority/artifacts. Нельзя удалить старый head/pinned root или выполнить live compaction для искусственного успеха. |
| Finalization ещё читает всё содержимое | Async ownership сохраняется; normal/sealed/package SHA/queue ACK только после действительного завершения. Сохранить EOS/drain/SC-001/003, не увеличить5s ради full scan. |

Для prefix первая реализация должна быть консервативной: GCM/DPAPI/native/hash error — терминальный отказ; degraded fallback только для уже разрешённой и доказанной semantic-invalid/missing категории, с полной проверкой выбранного прежнего snapshot/contiguous bytes. Отдельное извлечение исправных ранних DATA из дерева с authentication failure не авторизовано этим отчётом. Повторные reads никогда не возвращают уже скопированный partial output после failure.

## 8. Какие принятые нормы T115 нужно изменить прежде реализации

Текущий документ: [windows-protected-local-custody.md](/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup/specs/200-windows-desktop-app/contracts/windows-protected-local-custody.md). Ни одна строка ниже не внесена в него этим исследованием.

| Принятая норма / источник | Требуемая явная поправка, иначе решение запрещено |
| --- | --- |
| §1, строки13–20: per-block DPAPI/CNG SHA, без собственного AES/key/nonce lifecycle | Разрешить для больших v2 objects native AES-GCM + DPAPI key capsules; принять lifecycle fresh DEK/decrypt-only old epochs, nonce allocation, caps/rotation/error handling и время отзыва cached key. Это новая протокольная обязанность, хотя AES реализует Windows. |
| §2, строки39–72: actual native path proof, fixed block/index files | Сохранить native confinement/ACL/identities; добавить fixed packed file/default stream, container ID, actual GuardOwner lifetime и offset-ref authority. Не выдавать sharing за запрет всех link/ACL/ADS изменений. |
| §3, строки76–119: GRAFDP01 blocks, flat16-byte entries, физические bounds | Отдельный versioned v2 wire format: tree nodes/64-byte refs, bounds/AAD/tag/capsule/head framing и explicit subtree ZERO. v1 metadata остаются v1; никакого parse-error downgrade. Установить точные caps до codec реализации. |
| §4, строки123–136: CREATE_NEW versions, temp index + atomic rename + flush/validated reopen | Для v2 заменить на append-only records + исключение двух overwrite head cells, records-flush-before-head, ambiguous с первого head I/O и independent readback under continuous guard. Не утверждать, что in-place cells атомарны. |
| §4 ACK и [ProtectedCustodyFiles.h:80](/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup/apps/windows/RecApp/Storage/ProtectedCustodyFiles.h:80): обе indices и каждый DATA до выбора | Самая важная поправка: live ACK проверяет оба heads + delta + доказанное наследование immutable refs; fresh full closure при restart/ownership gap/ambiguous. Явно принять более позднее обнаружение latent old DATA corruption. Если нельзя — отказаться от проекта, не переименовать partial scan в full resolver. |
| §4, строки143–154 и audio resolver524–534: equal g1 допустима только metadata birth | Разрешить только v2 large-object independently protected equal-empty-g1 birth pair; задать interrupted birth/singleton/generation/fault rules. Действующий metadata no-rollback/no-auto-repair сохраняется. |
| §5, строки170–184: owned64MiB/cache2MiB/dirty4/pins32 и release copies перед reopen | Лимиты не увеличивать; заменить full arrays bounded paths/root stamps, учесть CNG backing/keys и buffers. Освободить writer copies, но передать живой GuardOwner actual finalizer/reader, не закрывать его ради reopen. Byte checkpoint256KiB и dispatcher/drain без изменений. |
| §5, строки225–247: physical peaks/transitive GC | Учесть capsules/nodes/append garbage/orphans и удержание целого container всеми двумя roots/pins/historical intents. Удаление отдельных block versions внутри active container не разрешено. Прежние disk/product limits остаются. |
| §6, строки251–273: verified pinned logical read/Clone/CopyTo/MF | Определить live-inherited proof отдельно от cold-full и per-read fresh authentication. Сохранить readonly semantics, bytesRead0/output wipe, cursor/EOF/borrowed buffer ownership, logical SHA/upload exact ranges. Не разрешать provisional cold reader без отдельного решения. |
| §7, строки275–298: actual async ownership/account/delete fences | Добавить общую life GuardOwner/DEK/OVERLAPPED до actual completion и write-capability revocation без early close. Тайм-аут не release/purge proof; никаких новых effects из stale completion. |
| §8/8.1, особенно строки441–454: package-state exact generation/length/SHA refs и полная validation referenced sealed contents | Для v2 добавить format/container/root stamp, точное удержание прошлых roots; явно определить, когда ссылка может использовать continuous live proof вместо повторного full content scan. После ownership gap referenced sealed content проверяется полностью до normal authority. Metadata slots/ledger проверяются полностью как прежде. T117 migration не считается реализованной. |
| §9, строки555–572; plan1376–1409; tasks558–561 | Дополнить T116 native regressions новой моделью и failure cuts; затем T118 acceptance. Текущая независимая проверка T115 относится к прежним нормам и не принимает этот вариант автоматически. |

Обязательные предварительные решения владельца: live incremental вместо fresh-all-data ACK; новый crypto/key/nonce protocol; packed persistent tree и неатомарные fixed heads; непрерывное владение вместо reopen; новая authority ссылок v2 и detection-time tradeoff. После согласования потребуются согласованные amendments contract/data-model/plan/quickstart и независимая scoped проверка/checklists/analyze. Сейчас они **не выполнены**.

Не изменять: user-scope/no-admin/offline; запрет plaintext application artifacts; v5 logical bytes/UUID/SHA/ranges; no empty ledger; fail-closed native errors; durability order/ambiguous ownership; SC/clock tolerances; pins/dirty/owned/cache/dispatcher limits; normal admission/delete/retention barriers. Не обещать невозможное: constant-time fresh64GiB reopen, гарантированный wall-time flush, full rollback detection без внешней authority, отсутствие OS plaintext paging или hardware bitrot.

## 9. Наименьший следующий шаг и последовательность внутри T116

Источник работы остаётся [T116, tasks.md:559](/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup/specs/200-windows-desktop-app/tasks.md:559), не новая GitHub задача. T115 принят для старой архитектуры; исследование не разрешает реализацию несовместимых изменений.

1. **Сначала решение T115.** Рассмотреть именно непрерывный guard + incremental ACK + fresh-full cold verify и новый crypto/tree/head layout. Зафиксировать вышеуказанные исключения и bounds, провести scoped независимую проверку/analyze; не менять T115 checkbox по факту существования отчёта.
2. **Первый вертикальный T116 участок после gate:** GuardOwner + небольшой packed fixture, three-level tree, две heads, один append/update и один pinned reader/Clone. Не весь MF/upload pipeline сразу. Доказать actual HANDLE continuity, отсутствие close/reopen gaps и запрет перезаписи content offsets. Сначала запланированные failure regressions, затем implementation по утверждённой норме.
3. **Codec/key tests:** строгое wire/context/range/overflow; wrong type/role/container/capsule; AES-GCM failure/output wipe; counter consumed при cancel/failure; restart новый encrypt DEK, old key decrypt-only; quota прежде CNG/DPAPI allocation и actual key destruction. Проверить ошибку provider/RNG, не только deterministic crypto fixture.
4. **Tree/commit tests:** операция на первом/последнем64GiB block и explicit ZERO без whole index allocation; root transition только от доказанного base; порча новых/старых/shared refs; каждый cut между records/head writes/flush/readback; torn heads/birth/singleton/ambiguous reconciliation; bounded constant records-per-checkpoint без N-sized cache. Сохранить current metadata rollback regressions.
5. **Windows native ownership gates:** уже открытый writer и writable mapping, hard link/ADS/reparse/rename/ACL, reader/Clone при writer release, last close/reacquire; cancel до/после publish и native operation actual completion;32 pins/64MiB/2MiB/4 dirty отказ до allocation. Нет early release при timeout/delete/account fence. Portable codec tests не доказывают sharing/durability.
6. **Подключить существующие consumers T116:** ProtectedCustodyFiles/Reader/Writer/Codec, V5LocalRecordingWriter/LocalRecordingPackage, MF adapter, bounded Sha256 logical reads, upload transport/playback без plaintext URL/temp и без UI/callback I/O. Не создавать второй lifecycle/dispatcher/queue; поддержка v1 по явной authority, не автоматическая конверсия всех journals.
7. **Только затем измерения и последующие gates:** повторяемый generated-data источник с прежней cadence/tolerance, стоимость checkpoint против logical length, холодный restart отдельно, seek/Stop и actual memory/native allocations/physical peaks. Нужен sustained результат по поддерживаемой Windows матрице, а не вывод из сложности. T117 migration и T118 end-to-end/physical acceptance остаются отдельными невыполненными воротами.

Этот вертикальный участок — минимальный полезный следующий implementation шаг; бессрочное улучшение provider/hash при неизменном полном scan не решает длинонезависимость. Если владелец не принимает изменение freshness ACK, безопасного масштабируемого следующего шага в пределах нынешнего контракта нет: можно только снижать константы и сохранять честный fail-closed отказ при отставании.

## 10. Первичные внешние источники

Документация ниже проверена для исследования; она описывает native primitives, но не является доказательством нашего нового протокола. Не использованы статьи поставщиков/блоги вместо Microsoft/NIST. Code-reviewer skill использован для проверки цепочки вызовов и отделения текущего поведения от предложения; deep-research — для первичных источников и явных противоречий; ov-experience-memory — только для прежней границы native proof/portable evidence, перепроверенной по текущему исходному коду.

- S1 — [Microsoft: CreateFileW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew): access/sharing, lifetime, mapping conflict, flags и metadata exception.
- S2 — [NIST SP800-38D, final2007](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-38d.pdf), §§8–9 и Appendix D: unique key/IV, key freshness, power-loss state и отсутствие встроенной replay защиты. Это ссылка на финальную публикацию, не принятие revision draft.
- S3 — [Microsoft: BCRYPT_AUTHENTICATED_CIPHER_MODE_INFO](https://learn.microsoft.com/en-us/windows/win32/api/bcrypt/ns-bcrypt-bcrypt_authenticated_cipher_mode_info) и [BCryptDecrypt](https://learn.microsoft.com/en-us/windows/win32/api/bcrypt/nf-bcrypt-bcryptdecrypt): nonce/AAD/tag и authentication failure.
- S4 — [Microsoft: BCryptGenRandom](https://learn.microsoft.com/en-us/windows/win32/api/bcrypt/nf-bcrypt-bcryptgenrandom): system-preferred RNG и проверяемый результат.
- S5 — [Microsoft: CryptProtectData](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata): user-scope защита, UI flags, integrity и lifetime native output.
- S6 — [Microsoft: File Streams](https://learn.microsoft.com/en-us/windows/win32/fileio/file-streams): per-stream sharing, stream enumeration и unnamed default stream.
- S7 — [Microsoft: Hard Links and Junctions](https://learn.microsoft.com/en-us/windows/win32/fileio/hard-links-and-junctions): aliases одного файла, не независимые content copies.
- S8 — [Microsoft: FILE_ID_INFO](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_id_info): volume/file identity, не cryptographic content freshness.
- S9 — [Microsoft: FlushFileBuffers](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-flushfilebuffers): file-level flush, required write access и admin-only volume flush.
- S10 — [Microsoft: CancelIoEx](https://learn.microsoft.com/en-us/windows/win32/api/ioapiset/nf-ioapiset-cancelioex): cancellation request отдельно от completion.

## 11. Дополнение 2026-10-03: рекомендован минимальный DPAPI packed/tree вариант

### 11.1. Поправка к рекомендации, не к принятой норме

**Фактического blocker для CryptProtectData/CryptUnprotectData на каждом bounded DATA/node/head не выявлено. Рекомендую этот вариант вместо обязательного AES-GCM/key/nonce lifecycle из основного текста.** Устранение O(N²) обеспечивает постоянное дерево и наследование доказательства под непрерывным GuardOwner, а не выбор шифра. Связь «packed + tree требует AES-GCM» в первоначальной рекомендации была необоснованной. Это дополнение имеет приоритет для предлагаемого минимального решения; прежний текст сохранён без изменения как история исследования. Нормативное принятие не заявляется.

Сохраняются один packed container на большой object/role, три уровня radix64, две head cells, actual native/async ownership, fresh full verification после любого gap и явный detection-time tradeoff. Вместо GCM **каждая** DATA, NODE и HEAD отдельно проходит принятые user-scope DPAPI protect/unprotect и application integrity checks. Убираются app DEK, capsules, nonce allocator, rotation, epoch key cache и AES key objects. Дополнительного RNG/key lifecycle нет; существующее создание opaque identities не меняется.

Основание в текущем коде: [ProtectedCustodyCodec.cpp:109](/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup/apps/windows/RecApp/Storage/ProtectedCustodyCodec.cpp:109) уже выполняет bounded nativeTransform с контекстной entropy, `CRYPTPROTECT_UI_FORBIDDEN`, проверкой результата/outputLimit и `SecureZeroMemory/LocalFree`; [sealBlock/openBlock:182](/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup/apps/windows/RecApp/Storage/ProtectedCustodyCodec.cpp:182) проверяют exact header/context/length/reserved и payload SHA. Эти primitives можно переиспользовать через отдельно versioned typed wire. Существующие публичные `sealBlock/openIndex` сами по себе не понимают container/node refs: расширить формат и validators потребуется, но заменить cryptographic primitive — нет.

Microsoft описывает CryptProtectData как защиту DATA_BLOB с session key, которым управляет API, MAC и optional entropy; API не требует от caller хранить DEK/nonce. В опубликованном интерфейсе не найден запрет на предлагаемые bounded records. Это вывод по интерфейсу и текущей реализации, не обещание latency или универсального output overhead: [CryptProtectData](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata), [DATA_BLOB](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/ns-dpapi-crypt_integer_blob).

### 11.2. Конкретные caps и контекст

Предлагается outer framing16 bytes, отдельные v2 magic/version/kind, общий typed plaintext header128 bytes. Это новые предлагаемые wire bounds, ещё не принятый формат. Header содержит magic/schema/kind/role/header size, store/object/container IDs, physical offset, logical selector/range base, record version, body length, flags/reserved и32-byte digest field. DATA digest — SHA-256 exact logical payload; NODE/HEAD digest — SHA-256 всего typed plaintext с обнулённым digest field, как нынешняя index checksum. Тип задаёт единственный алгоритм проверки digest; неизвестный kind не имеет default decode.

| Record | Plaintext input в DPAPI | Полный physical envelope cap | Проверка |
| --- | --- | --- | --- |
| DATA |128-byte header + payload P, `0<P≤262144`; max262272 bytes |`P+4096`; max266240 bytes =260KiB, **включая**16-byte framing |Exact ожидаемые IDs/offset/logical position/version/P, reserved0, payload SHA и exact envelope SHA из parent |
| NODE_L0/L1/L2 |128-byte header +64×64-byte refs =4224 bytes, exact |8192 bytes =8KiB, включая framing |Exact level/base range/offset/version/count64; whole-plaintext checksum, refs/flags/overflow/child types/extents и parent envelope SHA |
| HEAD0/HEAD1 |128-byte header +128-byte fixed root descriptor =256 bytes, exact |16384-byte fixed cell; framing задаёт checked envelope length≤16384, остальное padding0 |Exact slot/IDs/offset, checksum, generation/length/extent/tree params/root ref, live expected descriptor equality либо cold pair resolver |

`≤256KiB DATA` означает payload, **не** ciphertext record: уже действующий [blockEnvelopeLimit:175](/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup/apps/windows/RecApp/Storage/ProtectedCustodyCodec.cpp:175) разрешает payload+4096. Protected envelope260KiB читается/пишется несколькими I/O chunks≤256KiB. Если потребовать physical record≤256KiB при том же полном payload256KiB, такая формулировка противоречит положительному overhead; не уменьшать payload/cadence молча.

Указанные caps — app admission/validation limits, **не гарантия Microsoft размера DPAPI output**. До protect известен и ограничен plaintext; перед unprotect framing/input bounds проверяются до owned allocation/native call. Native output должен быть nonempty, в пределах cap и exact ожидаемой plaintext length до копирования/использования. Если protect output превышает record cap — явный отказ до append/head publication, не plaintext fallback/второй cipher/неограниченный resize. DPAPI самостоятельно выделяет native output до нашей проверки; hard owned64MiB не распространяется магически на его внутреннюю память. Прежнее separate measurement native allocations остаётся. Это ограничение существующего primitive, не новый blocker, требующий AES.

Context entropy: фиксированная сериализация domain `graf.custody.packed.dpapi.v2`, store/object/container IDs, role, **точный** record kind, physical offset, selector и immutable record version. Для DATA selector — logical block index; для NODE — base block index, level различается kind. Immutable version связывается с уникальной append offset, которая не переиспользуется. Для HEAD selector — slot0/1, physical offset фиксирован, entropy version0; изменяющаяся generation находится внутри protected typed descriptor и проверяется после unprotect. Это избегает необходимости узнать generation из незаверенного head до decrypt, аналогично нынешнему index entropy version0. Все эти поля точно повторяются/проверяются внутри protected plaintext; optional entropy — контекст, не секрет и не account authorization.

Expected context берётся из доказанного parent/root/native owner, а не из untrusted outer header. Child ref по-прежнему64 bytes: offset8 + envelope length4 + DATA payload length4 + exact child-envelope SHA32 + flags4 + reserved4 + version8. Root descriptor содержит root ref, generation, logical length/count, committed extent, tree params и нулевые reserved. Child exact envelope SHA включает framing и ciphertext, **не plaintext head-cell padding**; padding проверяется отдельно. Ссылки на key capsules отсутствуют. Ни один content/logical SHA не становится plaintext filesystem metadata.

### 11.3. TRUE не является доказательством целостности

Актуальные Microsoft remarks прямо предупреждают, что CryptUnprotectData иногда может вернуть success с повреждённым output; конкретный error code нельзя считать надёжным tamper detector. Требуются application-level integrity checks: [CryptUnprotectData, Remarks](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptunprotectdata#remarks). Это предупреждение учтено, не повод автоматически менять primitive.

Последовательность допуска каждой записи:

1. Проверить ожидаемые physical range/input cap/framing/type; для child сверить SHA **точного прочитанного envelope** с hash в уже проверенном protected parent, затем unprotect. Для нового candidate использовать заранее вычисленный expected envelope hash и после publication связать запись с проверенным head/root path.
2. Проверить BOOL; FALSE — native failure, без попытки объявить slot безопасным по одному `GetLastError`. TRUE лишь разрешает продолжить проверки; plaintext ещё не выдан caller.
3. Проверить exact output length, typed header/domain/context/IDs/offset/selector/version/body size/flags/reserved; затем DATA payload SHA либо NODE/HEAD full checksum и все semantic/tree/ref bounds. Return TRUE с corrupt output не проходит эту цепочку только потому, что native API сообщил success.
4. Только после всей цепочки использовать node refs/выдавать DATA bytes/создавать proof token. При любом failure — wipe owned/native output, release через actual lifetime, `bytesRead=0`, без частичного результата, ZERO substitution или normal fallback. Существующее разграничение native/semantic errors и строгая metadata authority не ослабляется.

NODE/HEAD checksum и hashes внутри protected parent — не самостоятельный MAC против пользователя, который вправе заново вызвать DPAPI. Они дополняют native protection в уже принятой threat model; нового криптографического доказательства против logged-in user/admin/full rollback не заявляется. Hashes не доказывают fresh readability старого DATA без чтения: прежняя detection-time поправка остаётся.

### 11.4. Работа и ресурсы остаются ограниченными

На один обычный sequential full-block checkpoint: одна DATA + три NODE + одна HEAD, то есть пять protect calls. При сохранении двух проверок новых records из §5.2 — четыре unprotect перед публикацией, четыре после и две для heads, всего10; дополнительно≤3 unprotect прежнего base path при отсутствии decoded-node cache. Birth, tail/range операции и группа≤4 dirty blocks имеют отдельную фиксированную границу, не счётчик по всем старым DATA. Не делать `readValidatedSnapshot()` поверх всего контейнера ради ACK и не превращать verified read обратно в возврат ciphertext с повторным caller unprotect.

Append≤284KiB на full block по выбранным caps, без capsules; steady checkpoint не копирует flat index. После proof establishment холодный logical block read требует≤3 nodes + одну DATA,≤284KiB и четыре unprotect, без обхода списка ключей. Cold full verification после ownership gap остаётся O(reachable bytes) с bounded streaming memory. DPAPI latency/native allocation/flush ещё требуют Windows проверки; постоянное число calls не является измеренным sustained-capture claim.

Owned64MiB, pins32, dirty4/1MiB, chunks256KiB, cache≤2MiB, dispatcher/drain остаются прежними. Для decoded cache допустимы, например, семь DATA blocks1.75MiB плюс≤256KiB nodes; DEK/key cache нет. Никаких per-block HANDLE, фоновой неограниченной очереди или полного persisted verified bitmap. Packed garbage/reserve/whole-container pinning/GC и настоящая async ownership из основного текста сохраняются. DPAPI вызов удерживает input/output/job owner до фактического возврата; cancel не освобождает память работающего native call.

### 11.5. Сокращённая norm-delta и следующий шаг

Это **tree/layout/proof delta, не crypto lifecycle delta**. Для выбранной альтернативы строки §8 этого отчёта читаются так:

| Область T115 | Что действительно требует решения |
| --- | --- |
| §1, crypto selection |User-scope DPAPI + CNG SHA-256 сохраняются; запрет собственного AES/key/nonce lifecycle сохраняется. Не принимать AES/DEK/nonce/rotation/capsules как обязательную поправку. Уточнить только применение DPAPI к новым typed DATA/NODE/HEAD records. |
| §2–3, layout/wire |Packed container/default stream и IDs; новые node/head kinds, точная v2 entropy/header/checksum,64-byte refs, radix64×3, explicit ZERO subtrees и перечисленные physical/plaintext caps. Прежние limited v1 metadata остаются без crypto replacement/parse downgrade. |
| §4, proof/publication |Incremental live ACK вместо fresh scan всех DATA; обе heads всегда checked; same-HANDLE independent readback под непрерывным guard вместо close/reopen. Records-flush→head-write→head-flush→validation; fixed head overwrite не объявлять atomic; post-first-head-I/O failure ambiguous. Решение о equal-empty-g1 birth pair/singleton должно быть явным. |
| §5–7, ownership/resources/read |Bounded paths/root stamps вместо flat copies; общий actual GuardOwner для pins/Clone/jobs; per-read full contextual/app integrity; current limits/cadence/tolerances/cancel/delete barriers сохраняются. Нет app key-cache/revocation/crypto-erasure поправок. |
| §8/8.1, references/restart/GC |Точный container/root stamp в protected package references; live proof reuse явно разрешается или запрещается. Любой ownership gap требует fresh full closure до normal authority; metadata no-rollback и whole-container historical/pinned retention сохраняются. Lazy cold authority не добавляется. |

Нужны принятие detection-time tradeoff и точного tree/head wire, scoped review/analyze и затем реализация **в T116**. Наименьший вертикальный участок: тот же GuardOwner + DPAPI DATA/NODE/HEAD + один persistent-tree update + обе head readbacks + pinned reader/Clone; сначала запланированные regressions на exact context/hash guards, `TRUE+corrupt output`, oversize output, failure cuts и ownership gap. Это предложение работ, не выполненные тесты. Сборки/runtime/norm/Git в этом дополнении не изменялись.

Если затем измеренный constant-work DPAPI путь не выдержит исходную cadence, это станет конкретным performance blocker для дальнейшего выбора primitive; сейчас такого измерения нет. Не оправдывать заранее новый AES lifecycle данными, полученными на старом O(N²) full resolver. Для решения владельца сейчас достаточно **DPAPI packed/tree + explicit detection-time change**, без криптографического расширения.
