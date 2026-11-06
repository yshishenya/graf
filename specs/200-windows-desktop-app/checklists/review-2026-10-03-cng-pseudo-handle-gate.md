# Независимый допуск до реализации: T116 / CNG SHA-256 pseudo-handle

Дата: 2026-10-03. **APPROVED — качество требований только к замене открытия SHA-256 provider на `BCRYPT_SHA256_ALG_HANDLE`.** Scoped analyze: **CRITICAL=0, HIGH=0, MEDIUM=0**, неразрешённых уточнений в этой области нет. Это не обзор будущей реализации, не доказательство ускорения и не приёмка полного T116 или Windows.

## Проверенная база и полномочия

- Каноническая рабочая копия: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`; фактическая Git-ветка `codex/200-windows-followup`; HEAD `99b00a579c24b50e320465b69d9a296038bc544d`.
- Проверяются текущие незакоммиченные bytes поверх HEAD. До записи отчёта: 23 изменённых/индексированных записи и 49 untracked; существующая работа не присваивается reviewer и не перезаписывается.
- `.specify/feature.json` указывает F200, эту ветку и этот HEAD. Read-only prerequisite `--json --paths-only` подтвердил канонические spec/plan/tasks; его поле `BRANCH=200-windows-desktop-app` — feature anchor, не фактическое имя Git-ветки. Обычный режим имеет запись feature marker и не выполнялся; `--require-spec` текущим скриптом не поддерживается. Обязательные файлы отдельно проверены на наличие. Analyze hooks commit выключены.
- Применены `code-reviewer`, местный `speckit-analyze`, AGENTS.md, индекс guidance и относящиеся правила worktrees/spec-kit-flow/product-gates/tracker-policy/github-issue-canon/release-and-validation; PRD и current-product-status прочитаны в относящейся области. Исторические журналы целиком не переоценивались.
- Lane: независимая проверка требований активного `high-risk-product` T116, с единственной разрешённой записью этого нового отчёта. Код, нормы, пять списков и их отметки, feature marker, Git/GitHub не изменяются. Сборки, исполнение C++/CTest, VM, приложение и микрофон не запускались.
- GitHub connector прочитал `yshishenya/graf` issue **#7444, OPEN**: `[200][P0][storage] T116: Защитить всю локальную цепочку записи без открытых временных копий`; labels `feature:200`, `priority:P0`, `area:storage`, `gate:pr-blocker`, `type:hardening`. Последнее изменение issue: `2026-10-02T19:09:23Z`; сверка выполнена 2026-10-03. Это существующий task-backed владелец; assignees отсутствуют, персональное назначение не утверждается. Новый issue, комментарий или закрытие не нужны и не выполнялись.

## Пять фактических списков

Все 112 актуальных CHK-пунктов прочитаны, существующие отметки независимо пересчитаны; применимые к SHA требования сопоставлены с текущими нормами ниже. Чужие UI/audio/route критерии не объявляются заново принятыми. Статистика — состояние требований, не 112 выполненных продуктовых испытаний.

| Список | Отмечено | Не отмечено |
| --- | ---: | ---: |
| requirements.md | 22 | 0 |
| audio-capture.md | 24 | 0 |
| advanced-routing.md | 14 | 0 |
| security.md | 27 | 0 |
| ux.md | 25 | 0 |
| **Итого** | **112** | **0** |

## Scoped analyze и трассируемость

| Обязательство | Текущая норма / покрытие | Вывод |
| --- | --- | --- |
| Допуск собственного storage-среза | spec.md:628; plan.md:1376; tasks.md:558–559; Constitution VI и quality gates | T115 `[X]`, T116 `[ ]`; открытые clock/T119 не блокируют этот отдельный SHA-шаг и не принимаются им. Исторический суффикс `missing` строки T115 не отменяет текущие marker/contract/plan acceptance. |
| Exact bytes, hash и отказ без запасного пути | FR-012/013/014/022; contract §§1,3,4,6; T115/T116; requirements CHK012/020, security CHK012–015/017–018 | Формат/диапазоны, integrity, ACK и deletion truth сохраняются. Hash API меняет механизм создания, не критерий доверия. |
| Native standard-user и границы платформы | FR-019; plan.md:108; Directory.Build.props:6,11; Package.appxmanifest:11; advanced-routing CHK002–004/011, security CHK021 | Минимум уже Windows 10 `10.0.19045.0`, Windows 11; no kernel/driver/elevation. Нет требования custom provider selection, HMAC либо изменения свойств SHA provider. |
| Ограниченные ресурсы, ошибки и последующая приёмка | SC-003/005/006/008; contract §§5–6,9; quickstart §12; T115/T116 с последующей T118 | Буфер 64 KiB, свежий hash каждого digest, metadata-only evidence, сохранность после отказа. Квоты/численные gates и общая runtime-приёмка неизменны. |

Конфликтов с Constitution II/III/IV/VI не найдено: не меняются видимый Stop/управление, серверная наблюдаемость, lifecycle/удаление и порядок независимой проверки. У шага есть покрытие существующими T115/T116; новой задачи без требования нет. Нет блокирующего дублирования, неоднозначного fallback или требования изменить нормы. Показатели относятся только к этому кандидату, не ко всей F200.

## Первичная документация и допустимость кандидата

Проверены актуальные страницы Microsoft Learn 2026-10-03:

1. [BCryptOpenAlgorithmProvider — Note и Remarks](https://learn.microsoft.com/en-us/windows/win32/api/bcrypt/nf-bcrypt-bcryptopenalgorithmprovider): для Windows 10+ рекомендованы pseudo-handles вместо повторного открытия/закрытия; открытие provider относительно затратно. Это обоснование выбранного механизма, не измеренный выигрыш GRAF.
2. [CNG algorithm pseudo-handles — SHA256 и Remarks](https://learn.microsoft.com/en-us/windows/win32/seccng/cng-algorithm-pseudo-handles): начиная с Windows 10 есть `BCRYPT_SHA256_ALG_HANDLE` (`0x00000041`). Handle общий и неизменяемый; `BCryptSetProperty` не допускается, kernel `IRQL=DISPATCH` не поддерживается. Здесь только user-mode и нет SetProperty, поэтому эти ограничения не требуют расширения области.
3. [BCryptCreateHash — hAlgorithm, pbHashObject, dwFlags](https://learn.microsoft.com/en-us/windows/win32/api/bcrypt/nf-bcrypt-bcryptcreatehash): принимает pseudo-handle; `nullptr/0` для object buffer оставляет allocation CNG и освобождение через DestroyHash. Сохраняются `nullptr/0` secret и flags=0; reusable hash не вводится.
4. [BCryptCloseAlgorithmProvider — STATUS_INVALID_HANDLE](https://learn.microsoft.com/en-us/windows/win32/api/bcrypt/nf-bcrypt-bcryptclosealgorithmprovider) и [BCryptDestroyHash](https://learn.microsoft.com/en-us/windows/win32/api/bcrypt/nf-bcrypt-bcryptdestroyhash): pseudo-handle не закрывается; реально созданный hash object уничтожается отдельно.

Текущий `Sha256.cpp:122–155` всё ещё открывает `BCRYPT_SHA256_ALGORITHM` на каждый NativeHash и закрывает `algorithm_` в деструкторе. Кандидат заменяет только конструктор на `BCryptCreateHash(BCRYPT_SHA256_ALG_HANDLE, &hash_, nullptr, 0, nullptr, 0, 0)` с проверкой NTSTATUS, удаляет `algorithm_` и Open/Close из этого класса, сохраняет DestroyHash/RAII. Windows stream/file остаются native; `sha256(string_view)` на PortableHash (`Sha256.cpp:159`) не меняется и не становится fallback при CNG error. API/header/CMake правки не требуются.

Не разрешены persistent/global/thread cache, повторное использование hash object, изменение block verification/ACK/index/DPAPI/encryption/file policy/quotas/route, новый lifecycle или обработка ошибок в посторонних callers. OS-owned общий pseudo-handle не означает app-owned cache либо общий изменяемый hash state.

## Обязательные prospective регрессии — до изменения production SHA

Это требования к будущей реализации тестов, не результаты их исполнения.

1. `NativeHashFailureTests.cpp:14–53`: убрать `HashFault::open` и старый Open fault wrapper; считать **каждый реальный Create attempt** до проверки fault. `testCreate` проверяет точное `BCRYPT_SHA256_ALG_HANDLE`, null object/secret, нулевые размеры/flags и в нормальном случае делегирует настоящему BCryptCreateHash. `HashFault::create` применяет `createOrdinal`, а не отказывает всем Create безусловно.
2. Вместо hash-provider `opens` использовать прозрачное имя `creates`/`hashCreates`; в `ProtectedCustodyFilesTests.cpp:36,113–123` перенести `fileTestHashOpen` на Create signature, `FileFault::hashOpen` → `hashCreate`, `hashes` → `hashCreates`. `opens` этого второго файла считает **CreateFileW**, а не BCrypt: его не переименовывать и не менять смысл file-IO counters.
3. Отдельные TU-local запретные guards/counters доказывают **0 Open, 0 Close, 0 SetProperty** именно в SHA translation unit, включая ошибки. Старый Open fault mechanism удалить; отрицательная проверка отсутствия вызова не является сохранившимся Open fault. Не менять чужие CNG/DPAPI operations и не добавлять production fault settings.
4. На каждый stream/file digest, включая пустой ввод, ровно один новый Create и Destroy для каждого успешно созданного hash; update/finish работают только с текущим объектом. Повторные, разные и перекрывающиеся потоки не делят mutable state; failed Create не даёт update/finish или retry через Open/portable. Проверять создание и lifetime, **не требовать уникального числового handle после Destroy**: ОС вправе повторно выдать его значение.
5. Для stream/file сохранить native success abc, binary/empty input, chunk boundaries, EOF/exception masks, bounded-read и отсутствие hash успешного prefix при read/update error. Negative Create/Update/Finish NTSTATUS даёт no-hash, без частичного digest и fallback; следующий независимый digest вновь успешен. После native faults portable identity имеет прежние bytes и 0 CNG calls; не объявлять memory API безусловно noexcept.
6. `NativeHashFailureTests.cpp:91–110`: сохранить seal/open block/index → `hashFailed` на Create/Update/Finish и ordinal=2 Update для многокускового ввода. Это тест отказа действующего primitive, не разрешение убрать/сократить проверки блоков или индекса.
7. `NativeHashFailureTests.cpp:133–140`: baseline перед первым UploadSend имеет три Create (media, playback, manifest); **Create fault ordinal=3** поражает только hash манифеста, даёт `invalidPackage`, Create attempts=3 и HTTP sends=0. `DesktopHttpTransport.cpp:177,896` остаётся неизменным; ordinal не переносить на Finish/Open и не подменять общей неисправностью всех hashes.
8. Во всех custody writer/metadata/snapshot сценариях (Tests:229,524,682,720,1231) перенос на Create сохраняет notCommitted/ambiguous, retained artifacts, sticky writer failure и запрет unsafe writes. **Allocation fault hook со std::bad_alloc обязательно переносится вместе с hash hook**: ordinal=1–4 snapshot по-прежнему даёт `allocationFailed`, не успешный второй slot; read error остаётся `ioFailed`, Create status error — `hashFailed`. Не удалять allocation coverage как «неиспользуемую» вместе с Open.

Нынешние tests перехватывают Open и ещё не доказывают новый путь. Их отсутствие в будущей дельте было бы блокером source review; оно не является неясностью требований до реализации. Следующий допуск требует независимого обзора изменённых source/test bytes и затем применимых native regression evidence. В этом обзоре запуск не разрешён.

## Exact SHA-256 проверенных bytes

Пути в таблице относительно канонического worktree. Это SHA-256 содержимого файлов, не Git blob IDs; HEAD сам по себе не удостоверяет dirty bytes.

| Файл | SHA-256 |
| --- | --- |
| `.specify/memory/constitution.md` | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| `.specify/feature.json` | `1b81ff28519b49d9c5072bb187369e8d1c4cab1e50e6a9091e2ccaa5c50f1705` |
| `specs/200-windows-desktop-app/spec.md` | `d778aa44725911288331beeddc5a2293333bf2fb39ab93e2087a471cdb4f1c0f` |
| `specs/200-windows-desktop-app/plan.md` | `34e64befcd775c85ee524a8d0e097d7d08805545cec92966bfdbf98d446f71cc` |
| `specs/200-windows-desktop-app/tasks.md` | `76c91845c3ce5da964351cca95b027562190bbc0fcb9f76b7159d0d021261287` |
| `specs/200-windows-desktop-app/quickstart.md` | `9946be5c60a192c2fcb92d7c8db1419827ff757fea8c13d40b9023b949ce1d59` |
| `specs/200-windows-desktop-app/data-model.md` | `b494c57fa6cff34c0128d674677f5fca09e647aabbf60aea15c2a53603c43848` |
| `specs/200-windows-desktop-app/contracts/windows-protected-local-custody.md` | `630b85b2a077788a90d23d5763561dce320e317aeddabe8ae5fe8810853bdba0` |
| `specs/200-windows-desktop-app/checklists/requirements.md` | `91fecd3ca4c79eba15faa3543fce18f8d5db1eb7a6664701c683c460d0d5bc55` |
| `specs/200-windows-desktop-app/checklists/audio-capture.md` | `4471fb8dc0fa82851c57c3c5e0bf49f4a5f94d838c082998488ecbdc15280cfd` |
| `specs/200-windows-desktop-app/checklists/advanced-routing.md` | `bd88f0588e806b16e93f7031645ed56384245343d20c7c41ab610a532620da12` |
| `specs/200-windows-desktop-app/checklists/security.md` | `50a47dd3ff25223665a77dae3ba163c8732fe52a9e7705a019544be563d817f9` |
| `specs/200-windows-desktop-app/checklists/ux.md` | `1a5a28f7226d7fc25bafdb8239b3d4bea2aeae0d4aad969eb89b45ec5b855801` |
| `apps/windows/RecApp/Storage/Sha256.cpp` | `cfad493c54a1b6f0db19bdc0aa80858e18e8396c8605b58b2a91ebea33e01ca2` |
| `apps/windows/RecApp/Storage/Sha256.h` | `e51b352aa346036708ad30867fed412b67000434b87d88aeb02c45549c43cc60` |
| `apps/windows/RecApp/Storage/ProtectedCustodyCodec.cpp` | `148899142a1568f9bc01c47ab63de07f3b5f8854a05faec8ed3b2e2775963fea` |
| `apps/windows/RecApp/Storage/ProtectedCustodyFiles.cpp` | `eb712a38f76eb5374f6ee4e3d964d15fb5ef92db2e212d20c77a166fd69bf142` |
| `apps/windows/Tests/GrafWindowsCoreTests/NativeHashFailureTests.cpp` | `813bc9c32a14a1189a67c61593545ca6094c1c02e477fa69dc3c5fff7f46efb0` |
| `apps/windows/Tests/GrafWindowsCoreTests/ProtectedCustodyFilesTests.cpp` | `7dc2b317729df8dc5410ee9c3e37dfebf543385980dd7c984c2a63626abd270c` |
| `apps/windows/Tests/GrafWindowsCoreTests/Sha256Tests.cpp` | `70bf9177f14bf328299ca44ce1d0de2c2853124b228e9f6515744ca2813cebba` |
| `apps/windows/RecApp/Upload/DesktopHttpTransport.cpp` | `34bfb5d5359c22c5de26bd790227414974d4804abdd6588e8e63734022e9fce1` |
| `apps/windows/CMakeLists.txt` | `400b57f98d791a6739aa5be0a7140ce9d63f8d114f14cff305a39d8792eb141d` |
| `apps/windows/Directory.Build.props` | `e3a21249e822df3c1201b2ba2df1941f44538f33e34bf8b2e07bd3ed4d3f4a6b` |
| `apps/windows/Installer/Package.appxmanifest` | `95bea5c39f980228a5238ab9384ff68c051bff8b79765a9e945b1be21c12ceed` |
| `AGENTS.md` | `384c41c0b1674a3daf75d0e57646379198295c3f8452012c8101fc6332bec58b` |
| `docs/agent-guidance/README.md` | `40e357e422c60915d2c4334c83b9ab74f5ef4c0df6ab8831e3ed16e281ba18a6` |
| `docs/agent-guidance/codex-worktrees.md` | `d7d8c9cce8315c17efaa1da05ece80c2542ca01b966f81fb848580104b785e1d` |
| `docs/agent-guidance/spec-kit-flow.md` | `5edf818b6ee27c7ee66d14edc003325ec7b16789eb1a195377cdeb901ae44887` |
| `docs/agent-guidance/product-gates.md` | `e5c39fb473dcf785f417b9785b0d6ba17fe23026906eedc08c0620c7a6f5d097` |
| `docs/agent-guidance/tracker-policy.md` | `06450200cabdef48000af51241564e9ee9e8d36b50c71e06a88f8c50b7365466` |
| `docs/agent-guidance/github-issue-canon.md` | `7cd5c1cde2bb51e3842cae9e3717b094fea9f6fbb33fb1a408e6d243f9d68bf3` |
| `docs/agent-guidance/release-and-validation.md` | `e3d24689a330634ec5ef87d829f8bcbf16bb7b81e0196b9d0baae4f49f27278d` |

Текущий Sha256.cpp также совпадает с pin в предыдущем ограниченном native-hash review; прочие старые pins/результаты не подменяют эту таблицу. До записи отчёта дважды совпали агрегат SHA-256 отсортированного `git ls-files -co --exclude-standard -z` → file SHA-256 list: `66f79cd896d639e086cc423251e13ada9eed80657c9ce2c65a803b3dad8b9ca1`, и агрегат `git status --porcelain=v1 -uall`: `2dae7ea51913e999ffd917e744e0c40cbd40ce6dc7f01917be5266e2d7cfb7c1`. Ignored файлы в этот агрегат не входят; feature marker проверяется отдельно по таблице.

## Решение и граница handoff

**Кандидат допускается к подготовке перечисленных регрессий и последующей минимальной реализации внутри T116. Нового blocker требований нет.** Reviewer не выполняет эту реализацию. При изменении закреплённых bytes/области требуется актуальная повторная source-проверка; этот отчёт не удостоверяет новую дельту. Source/runtime/performance gates будущего кандидата остаются pending; T116/#7444, T117/T118 и общая Windows-приёмка остаются открытыми. Ни ускорение, ни полный protected-storage поток, ни release-ready не заявляются.
