# T116 — независимый scoped review HTTP-тестов и worker teardown

Дата: 2026-10-10. Рецензент: независимый reviewer, `code-reviewer`.

Вердикт: **SCOPED SOURCE GO; C0/H0/M0/L0** для исправленных Capture HTTP-тестов,
регрессии `testWorkerTeardown` и двухфайлового production исправления frozen317.
Это не runtime/full/installed/release GO и не закрытие T116 или issue #7444.

## Точная привязка

- Canonical: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
- HEAD: `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; dirty changes сохранены.
- Frozen317: `/Users/yshishenya/Documents/graf-f200-scheduler317-native.1J53K1`.
- GREEN `source317.json`: `3157bc8cced43896c7ea2f1a9f836189150e6edc75f8342a8cf883f9a25e4384`.
- RED `red/source317.json`: `18405f85de9bc8dd03fa7689539e5792b8f9b2b2afbb60aa57f6a91f11dd08bd`.
- Reviewer независимо сверил 209/209 физических файлов каждого manifest.
  RED → GREEN изменяет ровно два production-файла scheduler; тесты одинаковы.
  Четыре приведённых ниже canonical файла совпадают с frozen317 GREEN.

| Файл относительно canonical | SHA-256 |
| --- | --- |
| `apps/windows/RecApp/Upload/DesktopUploadRecoveryScheduler.cpp` | `8d016a2a2f4c9ed37585860ec7a547f0d916a8e8c3e1778c5f2b42d6a9bcdbdf` |
| `apps/windows/RecApp/Upload/DesktopUploadRecoveryScheduler.h` | `9024168f93d4f33fa84f4ac3d0720d5acb9f25aa27c988dbbcbc88e496344efc` |
| `apps/windows/Tests/GrafWindowsContractTests/DesktopUploadRecoveryTests.cpp` | `7c5aa74d1afb7422b3e65ac394836c24b2be83d16af2c468a678d2b6adbb3583` |
| `apps/windows/Tests/GrafWindowsContractTests/NativeCaptureStorageIntegrationTests.cpp` | `ea58cb0eb8751a35f1939e56cf323bcd220eb958c526a58fb49fcfae09e75844` |

## Capture: исправление reader lifetime и negative cuts

Сохранено предыдущее source заключение: независимый expected group открывается
до `inspectProtected`, читает manifest/media/playback в charged `CustodyBytes`
порциями ≤256 KiB, независимо вычисляет полный stream SHA, сверяет sealed refs
и SHA сохранённых bytes. Все локальные COM readers/group уничтожаются до
открытия реального proof; genuine pair непрерывно удерживается worker.
Fake PUT сравнивает snapshots, а actual transport читает retained proof.
Сохранены точные bytes/ranges/index/hash и JSON session/finalize проверки.
Это устраняет повторное эксклюзивное открытие native leases, не увеличивая pins
или квоту и не добавляя plaintext fallback/temp.

Исторический reader-correction source SHA:
`38bb43ecdbb535b827d86c7353aa02069fd2a21fc9f221fa8d7b80de20a73f0c`.
Five-negative-cut промежуточный SHA:
`7c908be4a061d2dfd01a0973a3826fc2a3b88f6dd4d6e7018f04ace3d78c6fe2`.
В последнем был P2: сравнение полного заряда при разных живых cache blocks.
В текущем `ea58cb0e...` P2 снят: per-cut equality убрана, но обязательная EXACT
`usedBytes() == idleOwnedBytes` сохранена в `main --protected-upload` после
inspection completion, освобождения proof/expected и restart/drain (строки
1017 и 1050–1052). Немедленные weak expiry, release weak control/budget и
disk-unchanged проверки не удалены. Лимиты и итоговая leak-проверка не ослаблены.

Negative cuts (строки 775–823): cancel на missing-ranges, end за sealed size,
полная owned quota до body allocation, неверный ACK offset и wire `bad_alloc`.
Ожидаемые статусы соответствуют actual flow: invalid range/bad ACK →
serverRejected, остальные → retryableFailure; PUT counts 0/0/0/1/1.
Все требуют known server truth, not finalized и нулевые accepted bytes.
`assert((...std::array<std::uint64_t,3>{}))` защищён от template comma.
Сохранены owning request-copy после transport return, pointer/length/hash,
weak expiry и освобождение body/control. Cancel сбрасывается после синхронного
возврата, не во время native call. `CustodyBytes` заряжает и затирает snapshots.

## Worker teardown: RED и исправление

`testWorkerTeardown` (строки 948–980) использует два atomic barrier:
callback ждёт разрешения возврата; deleter последнего captured shared owner
сообщает вход и ждёт разрешения завершения. Main до callback return сбрасывает
свою копию lease. При остановленном deleter требуются busy, drain==0, pending
queue и отказ replacement flight. После release требуется ровно одно принятие.
Owning shared_ptr и atomics сохраняют lifetime; ожидания ограничены существующим
3-second helper. Тест не подменяет private scheduler state или done.

Production diff минимален: `execute` принимает `WorkerHandler` по значению;
mutable outer thread lambda передаёт его через `std::move`; строка 86 очищает
worker **до** release-store done на строке 87. Callback captures уничтожаются
в worker до того, как acquire-drain может принять результат/освободить lease.
Прежние protocol, owner/cancel decisions, selection и result application не
переписаны. Это не доказательство выхода самого thread или полной protected
storage/result интеграции; внешний flight capture ещё существует до выхода.

Reviewer прочитал сохранённые `portable317-red.json` и `portable317-red.log`:
build_exit=0, test_exit=8; assertion строки 974 —
`scheduler.busy() && scheduler.drain() == 0`. Журнал указывает 1.91 s;
main сообщил около 1.92 s. Исходники RED bound manifest совпадают физически.
Это независимое чтение сохранённого результата, не повторный запуск reviewer.

- RED receipt SHA-256: `24e30752ecd32a94f934e317e27f415e2692a25bb1442e41345d845f28c72cc7`.
- RED log SHA-256: `0a7b5a4e56fb11c02d374d96902387ff3aaf67598aedbafd795d5eacfbb69c69`.

## Обязательные незавершённые границы

ALL request/response/hash/serialization/config/result allocations, capacities,
control blocks и Debug proxies под общей 64 MiB квотой — ещё НЕ завершены.
Полная protected scheduler prepare full commit/adoption, storage-worker proof
и network launch/last release, fresh-current single result commit/adoption,
stale/publish/lost-poll/shutdown continuation — ещё НЕ завершены.
T120 и остальные consumer gates обязательны; global admission остаётся закрытым.
Частичный body/root fix не закрывает FULL T116/T117/T118 или hardware parity.

По сообщению main, native316 negative matrix выполняется последовательно,
portable317 GREEN — параллельно. Эти результаты здесь PENDING: reviewer не
читал их terminal receipts и не заявляет GREEN/native/full/installed PASS.
Исторические native301/312/313 FAIL не переименованы в PASS этим отчётом.

Reviewer выполнял только чтение исходников/diff, hash verification и
`git diff --check` для четырёх файлов (чисто). Сборки, тесты, VM/native jobs,
GitHub и внешние действия не выполнялись. Единственная разрешённая запись —
этот новый reviewer-owned отчёт; code/tasks/normative checklist markers не менялись.
