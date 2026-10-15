# Round273 — узкий REQUIREMENTS-addendum: два vector-поля Files::State

Дата: 2026-10-07. Reviewer-owned, 0 checkbox. High-risk-product, existing T116 / #7444.

## Решение

**SCOPED REQUIREMENTS GO — C0 / H0 / M0 / L0** для добавления только
`tokenUser(std::size_t{0})` и `directories(std::size_t{0})` в существующий
конструктор `ProtectedCustodyFiles::State`. Инициализаторы сохраняют порядок
объявления: directory, tokenUser, directories, trustedRoot. Прежние path copies
сохраняются. Constructor остаётся потенциально throwing, не noexcept.
Допуск обоих полей — не SOURCE GO, не Debug PASS и не разрешение других producers.

## Проверенные факты и граница вывода

Лично прочитан весь stderr
`/Users/yshishenya/Documents/graf-f200-pair-state273.gbcpVI/diagnostic-state273-stderr.log`;
receipt JSON разобран без изменения BOM/bytes, source204 map сопоставлен с
canonical. Receipt: temporary-diagnostic-not-acceptance, terminal true,
build_exit0, test_exit3. Reviewer VM/тесты не запускал.

Последний actual cut4 bytes16: `_Container_proxy_alloc → vector<unsigned char>
default ctor → ProtectedCustodyFiles::State::State → make_unique<State>(root)
→ openImpl → MigrationPair::read`. Cuts2/3 показывают path copy construction;
сведения об их classified refusal/retry сообщены main. Последующий cut4 и test3
не позволяют объявить full constructor/matrix успешными.

**tokenUser — прямое доказательство. directories — аналогия реализации, не
отдельный actual stack.** Это два обычных `std::vector<T, std::allocator<T>>`
в том же конструкторе, а не разные custom allocators. У count-конструктора
потенциально throwing контракт, в отличие от default/noexcept proxy пути;
тип элемента не требует создания элементов при count0. Та же минимальная
форма `Base(std::size_t{0})` уже существует в `CustodyVector` (Codec.h:16–30)
для сохранения Debug proxy failure classification. Поэтому второе добавление
можно допустить без искусственного отдельного аварийного запуска. Не заявляется
самостоятельно проверенное runtime поведение directories или чтение installed
MSVC vector header reviewer; фактическая native проверка обоих остаётся впереди.

До финального решения main сообщил actual installed MSVC14.44 read:
vector670–671 default ctor noexcept с `_Alloc_proxy`, vector678–680 explicit
count ctor без noexcept с `_Construct_n(_Count)`. Это main tool evidence,
не reviewer VM execution; оно поддерживает общий механизм для обоих vector<T>,
но не заменяет actual directories cut/retry или окончательный SOURCE review.

Source204 map:203 совпадают с canonical, единственное отличие — worker FilesTests;
Files.cpp совпадает. Не заявляется full204 current test applicability. Исходник
диагностического теста отдельный, его SHA сверён с receipt; instrumentation
остаётся внешним диагностическим материалом, не product/source acceptance.

## Минимальный разрешённый diff

```cpp
explicit State(const std::filesystem::path& root)
    : directory(root), tokenUser(std::size_t{0}),
      directories(std::size_t{0}), trustedRoot(root) {}
```

- Типы vector/allocator и расположение members не меняются. count ровно0;
  не добавлять reserve/предвыделение элементов, helper, wrapper или fallback.
- descriptor/security между tokenUser и directories остаются с прежними
  defaults; handles после trustedRoot тоже. Нулевой размер сохраняет отсутствие
  token bytes и retained Directory records до их существующего заполнения.
- Debug proxy allocations НЕ исчезают и НЕ освобождаются от cuts. Предложение
  меняет возможность распространения отказа, не quotas/charges или STL flags.
- В openImpl создание State по-прежнему после проверки root, внутри прежнего
  try/catch. При отказе count construction уже созданные members очищаются;
  native token/ACL/lock/content операции ещё не начаты. bad_alloc должен
  классифицироваться прежним allocationFailed; это требуется runtime проверить.
- tokenUser по-прежнему resize(size) только после native token-size query и
  bounds check; sid()/GetTokenInformation видят прежние actual token bytes.
- directories получает элементы только после открытия и проверки ancestor
  handles в lockDirectory. Прежние push_back, order, privateDirectory, handles
  и close-on-unwind/last-owner release не меняются. Packed-owner check читает
  заполненный vector только после successful Files.open, как прежде.

**Не разрешены** новые изменения path/iterator/State layout, inspect/indexName,
SDDL/string helpers, Directory constructors, другого PackedOwner::State,
move/return paths, quota/test ordinal/catch/flags или других producers. Будущий
actual stack — отдельное основание, не расширение этого разрешения.

## Нормативная трассируемость / scoped analyze

Base custody §2:46–65 требует native confinement/ACL/IDs и безопасного отказа;
FR-012/013/014/022 и existing T116:568 покрывают shared storage prerequisite.
Constitution III/IV/VI, принятые spec/plan/contracts и предыдущие narrow gates
не меняются. Source anchors: Files.cpp97–123 (members/constructor/token),
164–173 (directory lock/retention), 264–319 (sole creation/catches), 682–697
(packed friend reads). Новый schema/product decision/effect authority отсутствует;
блокирующего C/H противоречия этой конкретной границы не найдено.

После реализации необходимы fresh exact-source native Release/Debug с actual
allocation/cancellation cuts, cleanup/baseline/retry и retained lease assertions,
без отключения proxy ordinals; старые Files/open/discover/packed regressions
сохраняются. Отдельно подтвердить zero sizes и отсутствие ранней публикации при
отказе каждого count construction. Source inference не объявлять test PASS;
portable regression не доказывает native Debug proxy/ACL/DPAPI поведение.
Main сообщил portable46/46 PASS28.35s на State-copy+0ca2 snapshot, не на ещё
не реализованной vector правке. Это не native proof этого gate. Сообщённое
worker наблюдение repeated-separator unsafePath сохраняет actual inspect policy;
из этого gate не следует разрешение ослабить normalized-handle comparison.

## Identity / freshness / сохранение

Canonical `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`;
ветка `codex/200-windows-followup`; HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; dirty сохранён.
До записи146 files, все146 unchanged:10 текущих нормативных154 checked/0 open,
136 прочих/исторических документов; historical OPEN findings не новые norms.
Sorted basename<TAB>SHA256<LF> inventory146:
`ade4a68ca1d9dfe20ca726a55f25de5e3bac8804cbd4fe29900c736ae6ccc781`.
Tasks120/93/27, SHA `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`.
Before/after analyze/checklist/implement: registered1/enabled0 каждый, YAML
разобран, dispatched0. Prerequisites read-only подтвердили active Feature200.
Guidance/constitution/current norms переиспользованы с fresh hash verification;
`code-reviewer` и `speckit-analyze` полностью перечитаны и применены в узком scope.
Analyze сам read-only; пользователь отдельно разрешил этот новый report.

| Файл | SHA-256 |
| --- | --- |
| Files.cpp до предложенной vector правки | `d22acfc0ec3e605309f33394b47dd57d9de52b56b12e1721176cdfc0c38044b6` |
| source-state273.json | `aec6e131b2e33910dc985d4225ee1e44037ad496a5150869b6e9345167f20d5c` |
| diagnostic-state273-stderr.log | `611dbbd24221cbd49d8e79090ce399238224bd3629f0bd33ea62e0f25c977ab8` |
| diagnostic-state273.json | `29cda31bc7b30eea6fae07092dba33d87bb27c7bb35394b580daf58d735e949d` |
| diagnostic-FilesTests.cpp | `b29865b8012964ce5e8fdd77fd130614165ce3e769a5d2c8bcbe8d3e99262e57` |
| prior State path gate | `cd942a30dcca3b9ec486f7d00b2c72959b665782d19e78c484203520635b8a54` |

После записи лично проверены previous146 report hashes и source/normative
artifact hashes: unchanged. Единственная запись reviewer — этот новый0-checkbox
report; code/tests/spec/plan/tasks/GitHub/VM/hooks/commit не менялись.
SOURCE273/full T116–T120/H250/legacy AAC/physical x64/installed/app/release
остаются открыты. Это допуск только двух zero-count vector initializations.
