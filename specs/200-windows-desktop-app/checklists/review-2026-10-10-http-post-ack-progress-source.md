# T116 — scoped source review сохранения HTTP-прогресса после ACK

Дата: 2026-10-10. Независимый reviewer, `code-reviewer`.

Вердикт: **SCOPED SOURCE GO; C0/H0** только для сохранения известной
`UploadServerTruth` при `std::bad_alloc` из wire после принятого ACK.
Это не ALL-quota, preowned-terminal, runtime/full/installed/release GO
и не закрытие T116, T117, T118, T120 или issue #7444.

## Точная привязка

Canonical: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
HEAD: `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; dirty changes сохранены.

- Frozen318: `/Users/yshishenya/Documents/graf-f200-progress318-red.6CkbQ2`.
- `source318.json`: `685ec1b13d764fdc69e12c12f3cbd5197c40e3947193f203f1789456bd8606e9`.
- Frozen319: `/Users/yshishenya/Documents/graf-f200-progress319-green.gc4KoP`.
- `source319.json`: `a71ff9d628da82d874587ae73496f3e58895ed9a0679cc50f08e1f82b25aabd5`.
- Reviewer независимо сверил 209/209 физических inputs каждого manifest.
  Между manifest изменён ровно один production-файл; canonical 209/209
  совпадает с frozen319 на момент проверки. Тест не изменён.

| Файл относительно canonical | Frozen318 SHA-256 | Frozen319/canonical SHA-256 |
| --- | --- | --- |
| `apps/windows/RecApp/Upload/DesktopHttpTransport.cpp` | `50d8655a94484b35acd867c436c4df5993bd409ae7a1b0630076feb9cd7ad3dc` | `568ab0b76b1823bdc024ee5c7c9fb5a16c9d5a0a8658e3d465f2903021502736` |
| `apps/windows/Tests/GrafWindowsContractTests/NativeCaptureStorageIntegrationTests.cpp` | `a2f571035624f76bede9df4643d7daec3aa778b85d1cac8e64c921fc73664490` | `a2f571035624f76bede9df4643d7daec3aa778b85d1cac8e64c921fc73664490` |

## Конструкция и причина source GO

Общий `uploadPrepared` сохраняет прежний протокол. После создания локальной
truth и `withTruth` добавлен вложенный try вокруг протокола (строка 1070).
Catch `const std::bad_alloc&` (строки 1192–1197) возвращает retryableFailure
и переносит известную truth в terminal result, пока исходная truth ещё жива.
Отступы внутри try — механическое изменение; других изменений протокола нет.

После первого валидного PUT ACK принятый диапазон уже отражён в
`truth.acceptedBytes`. Ранее исключение второго missing-ranges уничтожало
локальную truth, а внешний protected-upload catch возвращал null truth.
Теперь раскрутка стека нового try освобождает protocol temporaries, но не truth;
терминальный catch сохраняет meeting/session flags, local id и accepted bytes.
Нет повторного запроса, следующего PUT, finalize или plaintext fallback.

Обычный `withTruth` намеренно продолжает копировать: если последующее
присваивание retryClass выбросит исключение, исходная truth не была потреблена
перемещением и доступна catch. Только terminal catch выполняет MOVE truth;
после этого протокол не продолжается. Endpoint/schema/auth/owner/cancel policy,
partSize, hash/ranges и body/read lifetime этой правкой не меняются.

## Независимо прочитанный RED318

Reviewer прочитал сохранённые `native318.json` и
`test318-Release-NativeCaptureStorageIntegrationTests.log`, не запускал тест.
Receipt: terminal=true, stage=expected_progress_loss_red,
mode=actual-protected-post-ack-progress-loss-red-only, configure_exit=0,
Release build_exit=0, test_exit=3, arguments=`--protected-upload`.
Receipt bound к приведённому source318 manifest.

Лог содержит actual_transport_bytes=pass, protected_result_adoption=pending,
затем `PROTECTED_HTTP after_ack_allocation=armed` и assertion строки 822
на failed.serverTruth: local id, meeting/session existence, not finalized,
acceptedBytes==acceptedBeforeFailure. Marker стоит непосредственно перед
throw второго missing-ranges после первого валидного PUT ACK. Это наблюдённый
сохранёнными артефактами ожидаемый RED потери прогресса, не GREEN исправления.

- RED receipt SHA-256: `28fc13417601531e48638a333091c4102f450e50f38249fba1257cd5c497f2d4`.
- RED test log SHA-256: `80a23380975df65425ba373dc8b5a196aaf061f5b8427f878aa909fcf25ea4ce`.
- Binary SHA из receipt: `39cb1ae53e1c87d9eb24a03be38e53a9ba947402e03bbd14851e5d536fcd6d49`;
  reviewer сам binary не исполнял и его bytes не сверял.

## Обязательные границы и исторический runtime snapshot

На момент этого отчёта runtime319 **PENDING**: по сообщению main запущены
два native targets Release/Debug последовательно после terminal318, portable
47 tests тех же frozen319 inputs — параллельно. Reviewer не читал terminal319
receipt и не заявляет GREEN. Имя artifact с green не является доказательством.
Этот snapshot не следует молча переименовывать в PASS по будущему результату.

Native317, по сообщению main: terminal 5/6 PASS, Debug Recovery timeout 124
при 300 s; full GO отсутствует. Возможная позднейшая проверка с 900 s bound
не выполнена reviewer и не подтверждена этим отчётом.

Исключение при самом создании/перемещении/возврате terminal result, включая
MSVC Debug служебные allocations, эта правка НЕ закрывает. Обычные withTruth
copies остаются. ALL request/response/hash/serialization/config/result
allocations, capacity/control/Debug под общей квотой — ещё НЕ завершены.
Нужен реальный preowned terminal до сети, а не поздняя charged копия результата.

64 MiB owned, cache 2 MiB, pins 32, native jobs 4 не увеличиваются;
4 MiB HTTP body и reads ≤256 KiB не подменяются меньшим partSize ради бюджета.
Полная prepare full commit/adoption → storage-worker proof/network launch →
fresh-current single result commit/adoption, stale/publish/readback/lost-poll,
owner-worker last release и shutdown continuation остаются обязательными.
Global storageWritable/localQueueComplete остаются false до всех требуемых
HTTP/playback/delete/T120 consumer gates. Direct transport PASS не закрывает их.

Reviewer выполнил только чтение исходников/diff/сохранённых RED artifacts,
сверку hash и одну разрешённую запись — этот новый reviewer-owned отчёт.
Код, tasks, normative checklist markers и другие reports не менялись;
build/test/native/VM jobs и внешние действия не выполнялись.
