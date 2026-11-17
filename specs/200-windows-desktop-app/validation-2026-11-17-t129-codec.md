# T129: промежуточная проверка формата метаданных

Дата: 2026-11-17. F200, действующий `high-risk-product`.
Это результат только структурного codec, не завершение T129/#8108.
Первый нативный writer v3, частичное чтение/воспроизведение, очистка WAV,
приёмка установленного приложения и выпуск остаются открытыми.

## Проверенный состав

Отдельный снимок получен через `git archive` основы
`70c32d6cf1ac2394d4123cbdc693bca4fb6e5d4c` с наложением ровно трёх файлов:

| Файл | SHA-256 |
| --- | --- |
| `apps/windows/RecApp/Storage/ProtectedCustodyMetadata.h` | `35e7782ee02348dd26b9474374d2ae6d2d79f2f2ed7620e4a5b997dac912831c` |
| `apps/windows/RecApp/Storage/ProtectedCustodyMetadata.cpp` | `77ee2200026139c701f51918e341439ebd55cc0fe7b2469f60a7fe8b1d89d300` |
| `apps/windows/Tests/GrafWindowsCoreTests/ProtectedCustodyPackageTests.cpp` | `04f1baefe272fda41c3b51ffddaa323f59f2d7f691c00978b3b153805af6816a` |

Контракт `contracts/windows-local-cache-cleanup.md`:
`527627747ebfc0488af9483866c4c13b4b171013dc6052d1581ad6e6923c79d8`.
Незакоммиченные изменения очистки памяти/SHA, профиля кабинета и F211 в
снимок не включались. Acceptance source сохранил прежние байты.

## Поведение

- Добавлен закрытый cleanup-only `graf.custody.package.v3`: точные поля,
  типы, перечисления, размеры, идентификаторы и границы поколений.
- Проверка base hash повторно использует прежний canonical writer v2.
  Формат v1/v2 и обычная запись package-state v2 сохранены.
- Receipt является исторической структурой. Он не выдаёт разрешение на
  чтение, отправку, изменение или удаление записи.
- Действующий полный reader отвергает cleanup в любой из двух slots до
  открытия содержимого. Нативный writer v3 не включён.
- Fixed значения и временные буферы сохраняют действующие правила учёта
  памяти и очистки; новый путь не вводит произвольный JSON DOM.

## Выполненные проверки

Независимый просмотр точного diff: `SCOPED SOURCE GO`, C0/H0/M0,
`.dev/t129-pure-codec-source-independent-20261117.md`.
Он не заменяет нативные и установленные проверки.

Сборка отдельного снимка на Mac, Release, существующие CMake/CTest targets:

| Этап | Выход | Время |
| --- | --- | --- |
| Configure | 0 | 0,712 с |
| Build | 0 | 25,217 с |
| CTest | 0 | 5,588 с |

Все четыре набора выполнены без failures/errors/skipped:
`Sha256Tests`, `ProtectedCustodyCodecTests`, `ProtectedCustodyPackageTests`,
`ProtectedPackedCustodyFormatTests`. Матрица v3: 36 положительных,
776 отрицательных случаев, `unmet=0`. Исторический литерал
`expected_current_reader=RED` в неизменном tests-first source сохранён;
фактический итог — process exit 0 и `unmet=0`.

Журналы и JUnit: `.dev/t129-isolated-portable-20261117/`.
Контрольные суммы:

- `ctest.xml`: `d06994683743f7a44a140673e96b0a14fdf4a8f9da29e32198807f7b6768359a`.
- `ctest.log`: `1df652e2ec4bd023887512e6172c5b24f2449319a43f60586e598cda36b4c4f8`.
- `result.json`: `a2db0b09e6a2cd7377f51666affe2371910284b8fb067f39b608380145ee4c9e`.

Временный каталог занимал 43 010 870 байт и удалён. Исходные SHA повторно
сверены после тестов. Микрофон, доверие сертификатам и данные записей
этой проверкой не использовались.

## Открытые условия

Нужны Windows/MSVC compile и реальные отказы обеих slots в полном reader,
revalidation и migration. Отдельно нужны v3 allocation/provider fault tests,
семантическая BOTH state machine, закрытый partial proof, проверка retained
содержимого и полного M4A EOS, Clone/close/drain и все consumers контракта §5.
До первого writer также обязательны cold/history/account/upload/calendar/
delete/purge и совместимость старого reader. Установленный rollback проверяется
отдельно; переносимые тесты его не доказывают.

Текущие GitHub Windows/governance проверки SHA
`0c99db6d456ce37d77b8eb8b7aaf9e24021c4684` завершились по часовому лимиту.
Они не являются PASS и не проверяли новый незакоммиченный codec.
Последующие exact-SHA проверки и merge остаются обязательными.
