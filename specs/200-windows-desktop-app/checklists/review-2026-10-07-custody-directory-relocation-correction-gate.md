# Round273 — corrected REQUIREMENTS GO: Directory / emplace

Дата: 2026-10-07. Reviewer-owned, 0 checkbox. High-risk-product, existing T116 / #7444.

**FINAL SCOPED REQUIREMENTS GO — C0 / H0 / M0 / L0** для явно подтверждённой
исправленной формы. REQ273-DIR-1 resolved на уровне требований; прежний NO-GO
`review-2026-10-07-custody-directory-relocation-gate.md` остаётся неизменным,
SHA `6a805bc91c17577c6780f187b2c8c7ddc2a424433dc5ab35e1a0720886144a66`.
Он относится к первоначальной форме без default constructor, не переписан.

## Точная разрешённая форма

```cpp
Directory() = default;
Directory(const std::filesystem::path& p, bool privateDir, Handle&& h)
    : path(p), privateDirectory(privateDir), handle(std::move(h)) {}
Directory(Directory&& other)
    : Directory(other.path, other.privateDirectory, std::move(other.handle)) {}
```

И единственная замена insertion:

```cpp
directories.emplace_back(path, privateDirectory, std::move(dir));
```

Сохраняются vector/count0 и member order path/privateDirectory/handle. Default
constructor нужен лишь для DefaultInsertable type requirement; runtime default
elements не добавляются. Его actual default-path fault safety НЕ доказана.
Custom constructors potentially throwing, не noexcept; path копируется до
noexcept Handle transfer. Нет Directory copy/duplicate native handle ownership.

## Failure flow и ограничения

Лично повторно проверен текущий openImpl: все lockDirectory calls внутри
неопубликованного unique State. При throwing relocation фабрика сразу unwinds
State до прежнего catch; не продолжает IO, не возвращает Files и не использует
старый State. Новый retry обязан быть fresh factory. Vector strong exception
guarantee не заявляется; сохранность moved-prefix handles/cleanup проверяется
actual matrix, а не выводится как PASS из этого допуска.

Исходный diagnostic cut17/build0/test3 остаётся failed evidence. Ранее прочитанные
stack, нормы и ownership trace переиспользованы; повторный giant audit не нужен.
Native Release/Debug all allocation/cancel cuts, baseline cleanup/retry и retained
lease regression обязательны перед SOURCE approval. Proxy cuts/flags/assertions
не ослаблять. Reviewer VM/тесты не выполнял.

Разрешены только указанная Directory форма и insertion. Нет reserve, нового
helper/allocator/dependency/schema/backend/registry, исключений quota или нового
default runtime flow. ACL/inspect/confinement/порядок locks/catches неизменны.
IndexName и остальные producers вне scope. Это не SOURCE GO, native PASS,
admission/effect/GC authority или завершение full T116/H250/app.

## Freshness / неизменность

Canonical `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`;
ветка `codex/200-windows-followup`; HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; dirty сохранён.
Files.cpp до разрешённой правки
`04e557d66a5047e97bc611228b3ab5d369e5c4d6c8c38fbe472be8822e0bbec9`;
FilesTests `0ca2a265214148995b785a578271a1d8cd46a9d7cbeb7d42eee4686cd9919aa0`.
Tasks120/93/27, SHA `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`.
Current10 normative154/0, исторические reports не новые norms. Existing
code-reviewer/scoped analyze и base custody §2/FR-012/013/014/022/T116 coverage
из неизменного NO-GO применимы; единственный H compatibility gap снят.
Новых C/H/M противоречий исправленной формы не выявлено.

До записи149 files inventory sorted basename<TAB>SHA256<LF>:
`941c5fc67d4e062c5c510ede85dbc62884bd6821f553027fdbb7757443615177`.
После записи лично проверены previous149 byte-identical, прежний NO-GO SHA,
source/test/task hashes unchanged и0checkbox. Единственная reviewer запись —
этот отдельный addendum. Code/spec/plan/tasks/markers/VM/GitHub/hooks/commit
не менялись. Main может реализовать только принятую точную форму и проверить её.
