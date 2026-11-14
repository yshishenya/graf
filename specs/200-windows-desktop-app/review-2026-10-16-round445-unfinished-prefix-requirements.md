# Round445 — независимый нормативный gate construction A

Дата: 2026-10-16. Отчёт сохраняет результат независимого requirements review и
scoped `speckit-analyze`, выданный до реализации и runtime-приёмки construction A.

## Вердикт и границы

**Нормативный GO для construction A в owner-only редакции. CRITICAL: 0; HIGH: 0
в проверенном scope.** Незавершённого нормативного перечитывания, блокирующего
этот шаг A, нет. Это не source GO, не runtime GO и не закрытие T116.

Репозиторий: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Ветка: `codex/200-windows-followup`.
HEAD: `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
Feature: `specs/200-windows-desktop-app`; risk lane: `high-risk-product`.
Работа принадлежит существующей T116/#7444. T116/T117/T118 остаются открыты.
Свежий OPEN #7444 сообщил Main; этот отчёт не заявляет независимую live-проверку
GitHub. GitHub не читался и не изменялся для сохранения отчёта.

## Проверенный нормативный delta

Проверены четыре новых append: plan, research, data-model и quickstart.
Предшествующий текст каждого из четырёх документов независимо восстановлен
удалением нового append и сопоставлен с его SHA из принятого report434:
предшествующие байты совпали. Последующая owner-only правка внутри append
свежепрочитана в plan/data-model/quickstart и отражена в SHA ниже.
Остальные шесть файлов из нормативного набора совпадают с baseline434.

Основные ссылки: `plan.md:2267`, `research.md:3054`, `data-model.md:634`,
`quickstart.md:1011`; неизменённый custody contract §4 задаёт complete480
recovery и запрет normal authority по незавершённым live refs.

Проверка была ограничена новым A и его согласованностью с действующими
spec/plan/tasks, constitution, relevant guidance и contracts. Исторические
runtime-отчёты не перечитывались как доказательство текущей реализации A.

## Scoped analyze

| Обязательство A | Основание и результат |
| --- | --- |
| Genuine owner/root/token binding | Вход только `StoreOwner/directory/cancel`; `readPackage` вызывается внутри, root берётся из owner. Caller-supplied root/Pair исключён, включая старую standalone форму без того же retained-root binding. Нормативного обхода не осталось. |
| Полная read-only custody проверка | Selected capturing/finalizing, canonical packed ref, BOTH package slots/heads и все reachable edges. Singleton/bad peer/key/IO/cancel/quota не дают успешный prefix. Согласовано с custody §4 и packed closure. |
| Exact prefix | `floor(validated logicalBytes/1920)` complete480 frames; нулевой prefix отклоняется. Нет padding, accepted-count/EOF/orphan authority или повторной AEC. Finite samples проверяются только в полном prefix ограниченным буфером. |
| Stream/fault/lifetime | Stat/Read/Seek/cancel проверяются, retained streams возвращаются в cursor0 с наблюдением shared sticky fault. Private result удерживает ту же пару, whole-group readers и token; последнее освобождение на worker, без destructor I/O. |
| Отсутствие новой authority | `UnfinishedInspection` не является `ProtectedInspection` или seal и не доказывает session/time/privacy/account. Нет разрешения playback/upload/delete/GC, writable accessor, нового формата, поля, pool или повышения пределов. |
| Неизменность данных | Нет записи queue/package-state/canonical/manifest/history/output. Quickstart требует сравнение paths/SHA всего generated root и проверку jobs/pins/owned-memory после last release. |
| Existing task coverage | Это внутренняя положительная часть T116 по FR-012/013/014 и custody recovery, а не новая пользовательская функция или задача. Tasks не меняются. |
| Явно незавершённый B | Existing-only writable metadata acquisition, unused/partial-role handling, manifest/privacy preservation, sealedDegraded ACK/ambiguous reconciliation и WAV/AAC остаются отдельной конструкцией до своих production edits. CREATE_NEW по прежнему пути не разрешён. |

В пределах этих обязательств противоречий CRITICAL/HIGH и необходимости нового
пользовательского решения не обнаружено. Общий процент реализации Feature 200
не вычислялся: scoped analyze не подтверждает весь продукт или весь T116.

## Checklist и tasks baseline

- Checklist: **197 Markdown-файлов; 430 checked / 0 unchecked**.
- Сохранён прежний baseline: 194 файла без трёх позднейших артефактов
  `review-2026-10-15-round410-privacy-history-requirements.md`,
  `start-owner-recovery.md`, `review-2026-10-16-start-owner-requirements.md`.
- SHA-256 baseline194: `98854ab3c8b80bd76dd87e003b726c85bc3f6415e0d6c53dd99b6dcbccd2053f`.
  Алгоритм: отсортированные basename, пробел, SHA-256 байтов файла, LF;
  затем SHA-256 конкатенации.
- Tasks: **120; 93 checked / 27 open**. T116 и следующие T117/T118 не отмечались.
- Сохранение старых markers не является новой runtime-приёмкой. Новые markers
  для A не выставлялись. Этот отчёт лежит вне `checklists/`, count197 сохранён.

## Свежие нормативные SHA-256

Пути без префикса относятся к `specs/200-windows-desktop-app/`.

| Файл | SHA-256 |
| --- | --- |
| spec.md | `0065a781efbfb52ef59f06ebe40b48e1cecd2f70d5c7e27f62a8570b43bc4e11` |
| plan.md | `e21c4e31c7aa8b080ef8ecce26b8f5753ae49671b0e7972b4140b7390d3c1ad5` |
| tasks.md | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| quickstart.md | `3ad75349890bdd93501bae5444ddf969a14de29d54541ee205cf6eb938026a40` |
| data-model.md | `1f20d0bb70f5e2c2c88acb4754293d154c34ed633ba71a170d7fd4aa0e0737c4` |
| research.md | `620c510832a33b1da6dad33a5b62055af819bd7929b89cab8ddfb48652761375` |
| contracts/windows-desktop-contract.md | `8bdafda168ea3f23407bbf70ea73ddf9bca1e27f1c38a1cfcbb6407a625cbba4` |
| contracts/windows-protected-local-custody.md | `38c86bcb8a600dcff0a76098099b1876c4d783238f39c44a8d3712dcce2c7f93` |
| contracts/windows-protected-packed-custody.md | `a1dedd9d5b7ce02e4a6c200a300b0423bcada82192217e2a79f9773428c4a7b5` |
| .specify/memory/constitution.md (от корня repo) | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |

## Следующий допустимый шаг и ограничения доказательств

Допустим предусмотренный планом tests-first шаг A. RED должен реально
собраться и выполниться: отсутствие API с compile/link failure не является
executable RED. Заявленный Main test-only SFINAE detector с fallback0 и
assert expected3frames может обеспечить такую границу; его конкретный diff
и runtime bundle этим нормативным отчётом ещё не проверены.

Будущие source/runtime reviews должны отдельно проверить реализацию binding,
BOTH closure, восстановление курсоров/fault, отказные cuts и unchanged disk.
Нет приёмки Native startup, sealing/history/output B, installed/hardware,
release или всего T116. Исторический Round444 PASS не перенесён на A.

Действия reviewer при сохранении: создан только этот отчёт. Код, нормативы,
tasks, checklist-маркеры, GitHub и commits не изменялись; VM/тесты не запускались.
