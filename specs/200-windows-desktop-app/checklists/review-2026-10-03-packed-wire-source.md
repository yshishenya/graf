# Независимая проверка prefix/Ref64 — 2026-10-03

Область: только `ProtectedPackedCustodyFormat.{h,cpp}`, `apps/windows/Tests/GrafWindowsCoreTests/ProtectedPackedCustodyFormatTests.cpp` и контракт §3, строки 55–126. Root/вложенные AGENTS учтены; режим проверки исходников без изменений реализации, запись только этого отчёта (docs-only scoped lane).

HEAD: `99b00a579c24b50e320465b69d9a296038bc544d`. Исходники, тест и контракт — untracked; результат относится к текущим байтам с SHA-256 ниже, не к содержимому коммита. Тест изменился параллельно и перечитан на финальном хеше.

## Результат C/H/M

**C=0, H=0, M=2.** Ошибок реализации в указанной области не найдено. M — пробелы проверок, не установленные нарушения формата.

- **M1 — независимый образец для старших байтов u64 отсутствует** (`Tests/.../ProtectedPackedCustodyFormatTests.cpp:53–66,108–112`). Единственный независимый образец Ref64 использует offset=32896 и version=7. Положительного примера с offset/version > UINT32_MAX и различными старшими байтами нет; полный блок проверяется лишь encode→decode. Согласованная ошибка обоих преобразований может остаться незамеченной. Нужны literal LE bytes для большого выровненного offset, многобайтной version и u32 lengths; отдельно допустимая сохранённая version < generation. Текущие `put/get` читают и пишут все байты правильно.
- **M2 — часть отказов проверяет только encoder** (`Tests/.../ProtectedPackedCustodyFormatTests.cpp:72–75,91–100,113–119`). Нулевая version, неверное выравнивание/offset до append, длина envelope≤16 или сверх cap, недопустимая DATA/NODE payload проверены главным образом через `encodeReference`, не прямыми повреждёнными Ref64 на входе `decodeReference`. Новые unknown/HEAD примеры имеют `bounds.kind=DATA`, поэтому отказ возможен только по несовпадению ожидаемого типа: нужны также bounds с тем же недопустимым kind. Добавить прямые decoder-примеры и offset≥parent, extent/parent<append. Это защитит общий `validShape` и вычитание границ от будущих регрессий; сейчас код отклоняет эти случаи.

## Проверенные свойства исходников

- **Точный формат/LE.** Prefix128: magic 0–7, schema/size 8/12, IDs 16/32/48, block/radix/depth 64/68/70, head/ref sizes 72/76, reserved 80–127. Ref64: kind/length 0/4, offset/version 8/16, payload/reserved 24/28, SHA 32–63. Запись побайтовая, без сериализации native struct/padding. Zero-initialized arrays обеспечивают reserved=0; prefix сравнивается целиком, Ref reserved читается явно. Unknown prefix/schema/constants/context и неподдерживаемая role отвергаются; HEAD/unknown не допускаются как Ref. EMPTY/ZERO требуют нулей во всех остальных полях.
- **Размеры/границы/переполнение.** Null или count≠128/64 отклоняются до чтения; extra/truncated не принимаются. Non-inline требует append offset≥32896, alignment16, version>0, envelope>16. DATA: 0<payload≤262144, envelope≤payload+4096; NODE: payload=0, envelope≤8192. Проверка payload предшествует сложению cap. `offset > UINT64_MAX-envelope` отвергает переполнение; затем version≤generation, exact expected kind/payload, parent≤extent и child end≤parent. Проверка offset>parent предшествует `parent-offset`, поэтому вычитание не переполняется. Равенство end=parent корректно для исключительной верхней границы; child start=parent не проходит. Через parent≤extent ограничивается и committed extent.
- **Parsing не authority.** Header:39–42 явно ограничивает ответственность. SHA только переносится; изменённый digest намеренно принимается тестом:133–135. Prefix не содержит role и одинаков для трёх разрешённых ролей — его совпадение не доказывает роль. Здесь нет I/O, DPAPI, SHA verification, proof или проверки selector/EOF/разрешённого ZERO. Проверка exact child envelope/SHA до DPAPI, typed context и внутреннего checksum остаётся обязанностью внешнего слоя по §3; его реализация не проверялась. `logicalLimit` здесь константа, не проверка descriptor/EOF.
- **C++17/no heap.** Использованы стандартные C++17 `std::array`, `std::optional`, fixed-width integers, циклы и алгоритмы над готовыми буферами; в этих функциях динамическое выделение памяти не требуется. Реальная сборка и зависимости вне разрешённых файлов не проверялись. `CustodyOwnedMemory::usedBytes()==0` до/после тестов (142–144) не доказывает отсутствие любых/временных heap allocations: это не перехват всех allocators. Заявление об отсутствии heap подтверждено анализом узких функций, не измерением native allocations.

## SHA-256 проверенного снимка

```text
a210c3331b36d8ae83ddcf3bd6af7e49c0e74fc2c2e4d1ef8bb573f6680fcc82  apps/windows/RecApp/Storage/ProtectedPackedCustodyFormat.h
073ddff71abf2e092b35426befb5648351022a424fa7d1e42cc7508754ce9fd6  apps/windows/RecApp/Storage/ProtectedPackedCustodyFormat.cpp
466b493bc7ccccbd765bf59484041e970c718420a34ce3487d2d0fbf8d4606f5  apps/windows/Tests/GrafWindowsCoreTests/ProtectedPackedCustodyFormatTests.cpp
7ff9a1a0b67f05fd1872358dcd33455331cdadb721e890f9f68295a3dc331eed  specs/200-windows-desktop-app/contracts/windows-protected-packed-custody.md
81a359199dcc0b35cb4a169412684600d567e855cf5598950a0e08270fc40b10  contract §3 (sed -n '55,126p', LF bytes)
```

Сборка/запуск тестов не выполнялись: native Windows и portable проверяет main, параллельных проверок нет. По сообщению main: native MSVC/W4/WX выявил C4244 только в test fills, исправленных explicit uint8_t без ослабления warnings; portable focused GREEN после stub/golden RED. Свежие portable all36PASS и native all37 build/CTest ещё ожидаются; здесь они не подтверждены. Хеш теста повторно сверен после этого уточнения; h/cpp не изменились.

Приложение, аудио, инвентарь, история, Git/GitHub, задачи и другие checklists не затронуты. T115 marker design-only принят и T116 открыт по вводным пользователя; эта проверка их не закрывает и не является review полной packed-v2 реализации.

## Дополнение: повторная проверка только исправлений M1/M2 — 2026-10-03

Предыдущие разделы сохранены без изменений. **После исправлений: C=0, H=0, M=1 (остаток M2, только полнота теста).** Новых ошибок реализации не установлено.

- **M1 закрыт** (test:81,136–152). Независимые literal bytes верно задают LE offset `0x0102030405060700`, version `0x1122334455667788`, envelope `0x00041000` и payload `0x00040000`. Encoder сравнивается с этим образцом, decoder получает сам образец, а не результат encoder. `version<generation` проверяется и на обычном Ref, и на большом. Offset выровнен, сложение границы и generation+1 не переполняются.
- **M2 частично закрыт** (test:92–113). Прямые повреждённые Ref64 теперь покрывают version=0, alignment, offset<append, envelope=16, DATA payload=0/>block, NODE payload≠0/envelope>8192, parent/extent и unknown/HEAD с SAME ожидаемым kind. **Остаётся изоляция DATA envelope cap** (test:102): bytes задают envelope=`0x1201`=4609 при payload=512 (cap=4608), но исходные bounds допускают до parent только1024 bytes. Поэтому тест продолжит отвергать Ref даже при отсутствии проверки DATA cap — по границе parent. Для закрытия остатка достаточно в этом примере задать корректные parentOffset=committedExtent≥offset+4609, например offset+8192, сохранив остальные ожидания. Код реализации корректен; менять его не требуется.

Свежий SHA-256 теста: `d3b31dc9ab0825e5d846cf5f06286c8ba901f3942049dc1815ae91d8f29d8612`. Хеши h/cpp повторно совпали с исходным отчётом: `a210c3331b36d8ae83ddcf3bd6af7e49c0e74fc2c2e4d1ef8bb573f6680fcc82` / `073ddff71abf2e092b35426befb5648351022a424fa7d1e42cc7508754ce9fd6`.

По сообщению main, native all37 и portable all36 прошли **до этой testdelta**. Новый focused portable и последующий native/freshall выполняет main; здесь результаты нового снимка не подтверждаются. Сборки, тесты, команды Git и расширение аудита не выполнялись; запись только этого дополнения.

## Финальное дополнение: остаток M2 — 2026-10-03

**Итог узкой проверки исходников: C=0, H=0, M=0. M1/M2 закрыты.** Проверены только две правки тестовых условий; предыдущие разделы сохранены.

- DATA cap (test:103–104): envelope=4609, payload=512, cap=4608; parentOffset=committedExtent=offset+8192 допускает весь envelope. Expected kind/payload/version и остальные условия корректны: отказ теперь изолирует превышение DATA cap, а не границу parent.
- Alignment (test:99–100): raw offset=32897, envelope=1024; end=33921≤parentOffset=committedExtent=34944. Offset находится в append region, остальные поля допустимы: отказ изолирует alignment16.

SHA-256 текущего теста: `119f67d748d2f9794960cd376e7cfbf92f273f15f47203ba6d27ea005aa35b6c`. h/cpp неизменны: `a210c3331b36d8ae83ddcf3bd6af7e49c0e74fc2c2e4d1ef8bb573f6680fcc82` / `073ddff71abf2e092b35426befb5648351022a424fa7d1e42cc7508754ce9fd6`.

По сообщению main, native37PASS и portable36PASS получены на предыдущем тестовом хеше `d3b31dc9ab0825e5d846cf5f06286c8ba901f3942049dc1815ae91d8f29d8612`. Повторная сборка/проверка нового хеша остаётся у main; результаты предыдущего снимка не перенесены на новый. Здесь не запускались тесты, сборки или команды Git. Итог касается только prefix/Ref64 и исправлений M1/M2, не всей packed-v2 реализации и не закрытия T116.
