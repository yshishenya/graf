# Round273 — REQUIREMENTS-addendum: Directory construction / vector relocation

Дата: 2026-10-07. Reviewer-owned, 0 checkbox, high-risk-product, existing T116 / #7444.

## Решение для точного предложения

**SCOPED REQUIREMENTS NO-GO as written — C0 / H1 / M0 / L0.** Два новых
конструктора и emplace устраняют доказанный path-move механизм, но предложенная
форма подавляет прежний default constructor Directory. При сохранённом
`directories(std::size_t{0})` необходим DefaultInsertable element type. Есть одно
конкретное, механически устранимое препятствие до кода; это не full-goal blocked.

| ID | Severity | Источник | Препятствие / минимальное уточнение |
| --- | --- | --- | --- |
| REQ273-DIR-1 | HIGH | Files.cpp106/113; proposed Directory constructors | User-declared constructor/move suppress implicit default constructor, но vector count0 требует DefaultInsertable. Сохранить `Directory() = default` только для well-formed type; никаких runtime default-element calls или изменения count0 |

Этот report НЕ выдаёт unconditional GO исходной форме. Рекомендуемое уточнение
ниже должно быть явно включено в предложение и допуск до реализации. Не нужно
нового task/schema/политики или перестройки storage. SOURCE/Debug PASS не выданы.

## Лично прочитанная диагностика

Stand `/Users/yshishenya/Documents/graf-f200-pair-strings273.bDVkHh`.
Прочитан весь diagnostic-strings273-stderr.log; receipt разобран readonly
с in-memory удалением BOM; diagnostic cpp SHA проверен. Terminal true,
mode temporary-diagnostic-not-acceptance, build0/test3. Reviewer VM не запускает.

Последний cut17 bytes16: `_Container_proxy_alloc → wchar string move ctor →
filesystem::path move ctor → State::Directory::Directory → vector
_Emplace_reallocate → push_back → lockDirectory → openImpl → MigrationPair::read`.
Cut15 — path copy при aggregate construction, cut16 — выделение vector storage;
они не заменяют full failure/retry matrix. Прямой механизм подтверждён, причина
не выводится из VM-гипотезы. Diagnostic failed receipt сохраняет свой статус.

Source204 map:203 совпадают с canonical, единственное отличие — current worker
FilesTests; Files.cpp совпадает. Не заявляется whole204 current test proof.

## Почему нужен default constructor

Текущий State использует обычный std::vector<Directory>, его единственный
инициализатор — count0. Тип Directory раньше был aggregate с неявным default
constructor; Handle уже non-copyable. Новые user-declared constructors удалят
именно возможность construction без аргументов, даже если никаких элементов
в runtime создавать не нужно. Это не проблема allocator budget/test timeout.

Первичный нормативный источник: [C++ draft vector.cons, §3–4](https://eel.is/c++draft/vector.cons#3)
требует DefaultInsertable для count constructor и создаёт n элементов. Нулевой
runtime count не снимает требования к типу. Installed MSVC template compile
reviewer не выполнял; это независимая проверка требования C++ и текущего use.

Минимальная обсуждаемая форма:

```cpp
Directory() = default; // Type requirement of vector(count0), not a new runtime use.
Directory(const std::filesystem::path& p, bool privateDir, Handle&& h)
    : path(p), privateDirectory(privateDir), handle(std::move(h)) {}
Directory(Directory&& other)
    : Directory(other.path, other.privateDirectory, std::move(other.handle)) {}
```

Оба custom constructors потенциально throwing, НЕ noexcept. `Directory()=default`
сохраняет прежнюю type capability; не вызывать его фактически и не менять
directories count0 на positive count/resize. Не добавлять новый default-path
runtime flow. Другой allocator constructor/noexcept обход не предлагается.

## Проверенная ownership граница остального предложения

Сохранить fields declaration order path/privateDirectory/handle. В прямом
конструкторе path копируется до handle member construction. Binding Handle&&
и std::move argument сами handle не передают; transfer происходит только после
успешной path copy, через существующий noexcept Handle move/std::exchange.
При path copy failure входной dir/other.handle всё ещё принадлежит своему owner.
Bool copy и Handle move после этого не бросают, body пустой.

В move constructor также копируется path прежде transfer. Copying Directory
с native Handle не вводится; implicit copy остаётся недоступной. Replace только
aggregate push_back на `directories.emplace_back(path, privateDirectory,
std::move(dir))`, без отдельного temporary Directory, reserve/registry/helper.

Custom throwing move не даёт vector strong exception guarantee для non-copyable
element. [C++ draft vector.modifiers, §2](https://eel.is/c++draft/vector.modifiers#2)
прямо не обещает сохранение исходного vector при таком отказе. Поэтому нельзя
объявлять old State usable/retryable после неудачной relocation или использовать
его для дальнейших IO. Для данного flow это не требует сильной гарантии:

- Sole lockDirectory callsites — openImpl:275/284/290/297/300/308. Ни один не
  перехватывает relocation exception и не продолжает с повреждённым State.
- Exception покидает фабрику; unique State unwinds до openImpl catch. Только
  после всех directory/identity checks происходит publication wrapper:317.
  До этого нет внешнего owner или borrowed view directories.
- Уже перенесённые handles принадлежат успешно созданным new elements;
  исходные становятся invalid. Cleanup новых elements/старого State должен
  закрыть оставшиеся handles без двойного close/leak. Это требование к actual
  MSVC reallocation/unwind matrix, НЕ уже выполненный runtime proof.
- Packed friend только читает retained directories:687–692 после successful
  Files.open; там нет lockDirectory/emplace/relocation published instance.
- Root/ancestor order, CreateFileW sharing, inspect/ACL, private flags и catches
  неизменны. createNew может ранее создать каталоги, как и до правки; не заявлять
  zero native namespace effects на всех failure paths. Pair read не создаёт их.

## Нормативная граница / последующая проверка

Base custody §2:46–65, Constitution III/IV/VI, FR-012/013/014/022 и T116:568
требуют сохранения confinement/private ACL/retained native ownership и честного
отказа. Предложение не меняет schema или права. Единственный H blocker —
DefaultInsertable совместимость; новой broader product ambiguity не найдено.

При уточнённом предложении перед SOURCE acceptance нужны fresh exact-source
Release/Debug all allocation/cancel cuts: construction, storage reallocation,
path copy каждого old/new element, partial moved-prefix cleanup, late failure,
baseline/retry и last-owner lease. Успешный retry — fresh factory, не old State.
Не отключать proxy cuts/assertions/флаги и не добавлять reserve для обхода.
Portable applicability не доказывает native Handle/Debug behaviour.

Вне scope: indexName, inspect/SDDL/другие paths, State layout/allocator/quota,
PackedOwner mutation, новые effects/GC/admission/recovery. Другой actual stack
потребует отдельного допуска. Полный SOURCE273 и T116/H250/app не закрыты.

## Identity / сохранение / evidence hashes

Canonical `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`;
`codex/200-windows-followup`, HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
Dirty сохранён. До report148 файлов:10 current normative154 checked/0 open и
138 прочих/исторических; previous148 byte-identical. Inventory sorted
basename<TAB>SHA256<LF>:
`530ab175af82a35319c9cd4659702f145823bf730b354cd34e1eb9a65e21ea73`.
Tasks120/93/27 SHA `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`.
All6 before/after analyze/checklist/implement hooks registered1/enabled0,
YAML разобран, dispatched0. Guidance/norms reused с fresh hashes;
code-reviewer/speckit-analyze полностью перечитаны, prerequisites active200.
Сам analyze read-only; разрешён только этот separate0-checkbox report.

| Файл | SHA-256 |
| --- | --- |
| Files.cpp до proposed Directory fix | `04e557d66a5047e97bc611228b3ab5d369e5c4d6c8c38fbe472be8822e0bbec9` |
| source-strings273.json | `c4c11252b2f6e44b93be6168e4f5b480ac25c987bad07a2e36362c850f9b7188` |
| diagnostic-strings273-stderr.log | `2a070f9a23c775d21fbd0a0349d1b368c25c32cd224b1d62d91010c69fc0bac4` |
| diagnostic-strings273.json | `29cda31bc7b30eea6fae07092dba33d87bb27c7bb35394b580daf58d735e949d` |
| diagnostic-FilesTests.cpp | `b29865b8012964ce5e8fdd77fd130614165ce3e769a5d2c8bcbe8d3e99262e57` |
| prior strings gate | `a8fc526a07a91c4a504282a1a25f962414164af07781fb2efe57f6bd603140c7` |

После записи лично проверено сохранение previous148 reports/markers и source/
normative hashes. Reviewer менял только этот новый0-checkbox report, не code/
tests/spec/plan/tasks/GitHub/VM/hooks/commits. Решение finite: уточнить один
default constructor, затем scoped gate decision; не повторять full historical audit.
